from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QLabel,
    QComboBox,
)
# 兼容作为包导入与单文件直接运行的场景
try:
    from .icon_utils import load_icon  # 包内相对导入（推荐）
except Exception:  # pragma: no cover - 回退路径
    try:
        from uiLAYER.icon_utils import load_icon  # 作为顶层包绝对导入
    except Exception:
        from icon_utils import load_icon  # 最后回退（依赖当前工作目录位于项目根或 uiLAYER 内）
from PyQt6.QtCore import pyqtSignal, QObject, QThread, QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
import os
import pickle
from pathlib import Path
import json
from typing import Iterator
# from html import escape
import requests
import pandas as pd

# 导入性能管理器
try:
    from config.performance_manager import performance_manager
except ImportError:
    # 如果导入失败，创建一个简单的性能管理器
    class DummyPerformanceManager:
        def should_monitor_performance(self): return True
        def is_fast_mode_enabled(self): return False
        def is_cache_enabled(self): return False
        def get_cached_response(self, prompt): return None
        def cache_response(self, prompt, response): pass
        def start_timer(self): return 0.0
        def end_timer(self, start_time, operation=""): return 0.0
        def get_model_setting(self, key, default): return default
        def get_performance_setting(self, key, default): return default
    
    performance_manager = DummyPerformanceManager()

# 导入API配置
try:
    from .api_settings_dialog import load_config, get_configured_vendors
except Exception:
    try:
        from uiLAYER.api_settings_dialog import load_config, get_configured_vendors
    except Exception:
        from api_settings_dialog import load_config, get_configured_vendors


class ChatWidget(QWidget):
    DEBUG = True  # 设置为 False 可关闭调试输出
    """一个简单的聊天窗口，用于与 AI 助手交互（目前仅本地回显）。"""

    def __init__(self):
        super().__init__()
        self._threads = []  # 跟踪后台线程，防止提前销毁
        self._init_ui()

    # --- 信号 ---
    # 仅保留用于流式响应的后台工作器

    class _StreamWorker(QObject):
        """专用于流式响应的后台工作器。"""
        def __del__(self):
            if ChatWidget.DEBUG:
                print("[Debug] StreamWorker 对象被销毁")
        chunk = pyqtSignal(str)
        finished = pyqtSignal(str)

        def __init__(self, prompt: str, gen_func):
            super().__init__()
            self._prompt = prompt
            self._gen_func = gen_func  # 需返回一个逐段产出的生成器

        def run(self):
            if ChatWidget.DEBUG:
                print("[Debug] StreamWorker start, prompt:", self._prompt)
            buffer: list[str] = []
            try:
                for part in self._gen_func(self._prompt):
                    if part:
                        buffer.append(part)
                        self.chunk.emit(part)
                reply = "".join(buffer)
                if not reply:
                    # 确保始终有最终内容，避免 UI 无输出
                    reply = "[未收到内容]"
            except Exception as e:
                reply = f"[流式出错: {e}]"
            if ChatWidget.DEBUG:
                print("[Debug] StreamWorker finished")
            self.finished.emit(reply)

    def _init_ui(self):
        self.setObjectName("ChatWidget")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # -------------------- 聊天记录显示区（基于 Web 引擎渲染 Markdown + Mermaid） --------------------
        self.web_view = QWebEngineView()
        assets_html = (Path(__file__).parent / "assets" / "chat_renderer.html").resolve()
        self.web_view.setObjectName("ChatWebView")
        # 使用原生路径字符串，避免部分 Windows 环境下 as_posix 路径导致加载异常
        # 追加 mtime 查询参数，避免 QWebEngine 缓存旧版 HTML/JS 导致未定义错误
        try:
            mtime = int(assets_html.stat().st_mtime)
        except Exception:
            mtime = 0
        url_with_q = QUrl.fromLocalFile(str(assets_html))
        url_with_q.setQuery(f"_v={mtime}")
        self.web_view.setUrl(url_with_q)
        # 页面加载就绪与 JS 调用排队
        self._page_ready = False
        self._pending_js: list[str] = []

        def _wrap_js_for_chatapi(raw_script: str) -> str:
            # 在页面端等待 ChatAPI 挂载完成后再执行，避免"什么都没有"的现象
            # 同时包一层 try/catch 防止个别注入失败中断
            return (
                "(function(){\n" 
                "  var __exec = function(){ try { " + raw_script + " } catch(e){} };\n" 
                "  if (window.ChatAPI) { __exec(); } else { setTimeout(__exec, 80); }\n" 
                "})();"
            )
        def _on_loaded(ok: bool):
            self._page_ready = bool(ok)
            if self._page_ready and self._pending_js:
                page = self.web_view.page()
                for script in self._pending_js:
                    try:
                        if page is not None:
                            page.runJavaScript(_wrap_js_for_chatapi(script))
                    except Exception:
                        if ChatWidget.DEBUG:
                            print("[Debug] runJavaScript(queued) 执行失败")
                self._pending_js.clear()
        try:
            self.web_view.loadFinished.connect(_on_loaded)
        except Exception:
            pass
        main_layout.addWidget(self.web_view)

        # -------------------- 顶部工具区 --------------------
        tool_layout = QHBoxLayout()
        # 折叠/展开按钮（如图所示的黑底白条风格）
        self.btn_collapse = QPushButton("▍")
        self.btn_collapse.setFixedSize(24, 24)
        self.btn_collapse.setToolTip("折叠/展开聊天区域")
        self.btn_collapse.clicked.connect(self._toggle_collapsed)
        self.btn_collapse.setStyleSheet(
            "QPushButton { background-color: #F5F5F5; color: #333333; border: 1px solid #CCCCCC;"
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #3A6FE2; color: #FFFFFF; }"
        )
        
        # API选择下拉框
        tool_layout.addWidget(QLabel("API:"))
        self.api_combo = QComboBox()
        self.api_combo.setToolTip("选择已配置的API厂商")
        self.api_combo.setStyleSheet(
            "QComboBox { background-color: #FFFFFF; color: #333333; border: 1px solid #CCCCCC; border-radius: 4px; padding: 2px 6px; }"
            "QComboBox:hover { background-color: #F5F5F5; border: 1px solid #3A6FE2; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #333333; }"
        )
        self.api_combo.setFixedWidth(120)
        self.api_combo.currentTextChanged.connect(self._on_api_changed)
        tool_layout.addWidget(self.api_combo)
        
        self.btn_settings = QPushButton("API设置")
        self.btn_settings.setIcon(load_icon("settings.png", "preferences-system"))
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_settings.setStyleSheet(
            "QPushButton { background-color: #F5F5F5; color: #333333; border: 1px solid #CCCCCC; border-radius: 4px; padding: 2px 6px; }"
            "QPushButton:hover { background-color: #3A6FE2; color: #FFFFFF; }"
        )
        self.btn_test = QPushButton("测试连通性")
        self.btn_test.setIcon(load_icon("network.png", "network-workgroup"))
        self.btn_test.clicked.connect(self._start_connectivity_test)
        self.btn_test.setStyleSheet(
            "QPushButton { background-color: #F5F5F5; color: #333333; border: 1px solid #CCCCCC; border-radius: 4px; padding: 2px 6px; }"
            "QPushButton:hover { background-color: #FF6B35; color: #FFFFFF; }"
        )
        # 是否显示思考内容（通过提示词引导模型输出"思考/答案"两段，可读推理并非模型内部隐私权重）
        self.cb_show_thoughts = QCheckBox("显示思考")
        self.cb_show_thoughts.setToolTip(
            "开启后，提示词会要求模型先输出'思考'再输出'答案'两部分；\n不保证与模型真实内部推理一致，仅供参考。"
        )
        # 用户手册选项，控制是否查看用户手册
        self.cb_use_manual = QCheckBox("是否查看用户手册")
        self.cb_use_manual.setToolTip(
            "选中时启用向量检索查看用户手册，不选时直接调用大模型提高响应速度。"
        )
        self.cb_use_manual.setChecked(True)  # 默认选中，启用手册查看
        
        # 长文本模式选项，允许使用更多token输出更详细的回答
        self.cb_long_text_mode = QCheckBox("长文本模式")
        self.cb_long_text_mode.setToolTip(
            "选中时允许使用3倍token，要求至少输出500字文本，提供更详细的回答。"
        )
        
        tool_layout.addWidget(self.btn_collapse)
        tool_layout.addStretch()
        tool_layout.addWidget(self.cb_use_manual)
        tool_layout.addWidget(self.cb_long_text_mode)
        tool_layout.addWidget(self.cb_show_thoughts)
        tool_layout.addWidget(self.btn_test)
        tool_layout.addWidget(self.btn_settings)
        main_layout.addLayout(tool_layout)
        
        # 初始化API选择下拉框
        self._load_api_options()

        # -------------------- 输入区 --------------------
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入消息后按 Enter 或点击发送…")
        self.input_edit.returnPressed.connect(self._send_message)
        self.input_edit.setStyleSheet(
            "QLineEdit { background-color: #FFFFFF; color: #333333; border: 1px solid #CCCCCC; border-radius: 4px; padding: 4px; }"
            "QLineEdit:focus { border: 2px solid #3A6FE2; }"
        )
        self.input_edit.setFixedHeight(28)
        self.send_btn = QPushButton("发送")
        self.send_btn.setIcon(load_icon("send.png", "mail-send"))
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setStyleSheet(
            "QPushButton { background-color: #3A6FE2; color: white; border: none; border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #2B57C1; }"
            "QPushButton:pressed { background-color: #1E3F88; }"
        )
        self.send_btn.setFixedHeight(28)

        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)

        # 思考指示条（波动动画）
        self.thinking_label = QLabel("")
        self.thinking_label.setStyleSheet(
            "QLabel { color: #6B7280; padding: 2px 0; }"
        )
        self.thinking_label.hide()
        main_layout.addWidget(self.thinking_label)

        # 将输入区包裹为容器，便于整体隐藏
        from PyQt6.QtWidgets import QWidget as _QW
        self.input_container = _QW()
        self.input_container.setLayout(input_layout)
        self.input_container.setFixedHeight(36)
        main_layout.addWidget(self.input_container)

        # 伸展策略：聊天区占满，其余控件仅按内容所需高度
        try:
            main_layout.setStretch(0, 1)  # web_view
            main_layout.setStretch(1, 0)  # tool_layout
            main_layout.setStretch(2, 0)  # thinking_label
            main_layout.setStretch(3, 0)  # input_container
        except Exception:
            pass

        # 折叠状态与动画定时器
        self._collapsed = False
        self._thinking_timer = QTimer(self)
        self._thinking_timer.setInterval(120)  # ms
        self._thinking_timer.timeout.connect(self._update_thinking_animation)
        self._thinking_frame = 0
        # 思考动画字符
        self._thinking_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def hide_internal_collapse_button(self) -> None:
        """供外部调用：隐藏内部折叠按钮（当主窗口有全局折叠按钮时避免重复）。"""
        if hasattr(self, "btn_collapse"):
            self.btn_collapse.hide()

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------
    def _send_message(self):
        text = self.input_edit.text().strip()
        if not text:
            return
            
        # 检查是否选择了有效的API
        current_vendor = self.api_combo.currentText()
        if current_vendor == "请先配置API":
            self._append_message("🤖 助手", "请先在API设置中配置API密钥，然后选择要使用的厂商。")
            return
        
        # 添加性能监控
        import time
        start_time = time.time()
        
        # 显示用户消息
        self._append_message("🧑 用户", text)
        self.input_edit.clear()
        # 纯粹流式：启动 Web 渲染区域中的助手消息（Markdown 渲染开启）
        self._run_js("window.ChatAPI && ChatAPI.startBotMessage(true);")
        # 重置流式状态标记
        self._received_stream_chunk = False
        # 显示思考动画
        self._start_thinking_animation()
        # 启动后台线程（流式）
        if ChatWidget.DEBUG:
            print(f"[Debug] 创建后台流式线程处理问题: {text}")
            print(f"[Debug] 开始时间: {start_time}")
        self._stream_buffer = ""
        worker = ChatWidget._StreamWorker(text, self._stream_ai_reply)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.chunk.connect(self._on_ai_chunk)
        worker.finished.connect(lambda r: self._on_ai_reply(r, worker, thread, start_time))
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda: (self._threads.remove(thread) if thread in self._threads else None))
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()

    def _on_ai_reply(self, reply: str, worker: QObject, thread: QThread, start_time: float = 0.0):
        # 纯流式：最终不再替换整段，内容已在分片阶段逐步写入
        if ChatWidget.DEBUG:
            print("[Debug] 主线程收到回复，线程结束")
            if start_time:
                import time
                elapsed = time.time() - start_time
                print(f"[Debug] 总响应时间: {elapsed:.2f}秒")
        # 若未收到任何分片，则直接把最终回复整体写入
        try:
            final_text = reply or ""
            if not getattr(self, "_received_stream_chunk", False) and final_text:
                self._run_js(f"window.ChatAPI && ChatAPI.appendBotChunk({json.dumps(final_text)});")
            # 结束并触发布局与 Mermaid 渲染
            self._run_js("window.ChatAPI && ChatAPI.finalizeBotMessage();")
        finally:
            worker.deleteLater()
            # 重置状态
            self._stream_buffer = ""
            self._received_stream_chunk = False
            # 停止思考动画
            self._stop_thinking_animation()
            # 标注本次是否回复了 Markdown 内容（当前方案统一为 True）
            self._last_bot_markdown = True

    def _on_ai_chunk(self, part: str) -> None:
        """逐段在同一行尾部追加文本（纯粹流式，不重绘整段）。"""
        # 直接将增量文本注入到 Web 渲染器中
        safe_part = part or ""
        self._run_js(f"window.ChatAPI && ChatAPI.appendBotChunk({json.dumps(safe_part)});")
        # 标记已收到分片
        self._received_stream_chunk = True
        
        # 优化：减少UI更新频率，提高响应速度
        if hasattr(self, '_chunk_buffer'):
            self._chunk_buffer += safe_part
        else:
            self._chunk_buffer = safe_part

    def _open_settings(self):
        try:
            from .api_settings_dialog import ApiSettingsDialog
        except Exception:
            try:
                from uiLAYER.api_settings_dialog import ApiSettingsDialog
            except Exception:
                from api_settings_dialog import ApiSettingsDialog
        dlg = ApiSettingsDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------
    # 连通性测试（后台线程执行）
    # ------------------------------------------------------------------
    def _start_connectivity_test(self) -> None:
        # 纯流式：在 Web 渲染器中插入一次助手消息（Markdown 渲染开启）
        self._run_js("window.ChatAPI && ChatAPI.startBotMessage(true);")
        self._stream_buffer = ""
        self._received_stream_chunk = False
        # 开始思考动画
        self._start_thinking_animation()
        # 使用流式工作器，即便只产生一次性结果也走统一的流式管道
        worker = ChatWidget._StreamWorker("__connectivity_test__", lambda _:
                                          self._stream_connectivity_test())
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.chunk.connect(self._on_ai_chunk)
        worker.finished.connect(lambda r: self._on_ai_reply(r, worker, thread))
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda: (self._threads.remove(thread) if thread in self._threads else None))
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()

    def _stream_connectivity_test(self):
        """将连通性测试以流式形式输出（此处简单为一次性整体产出）。"""
        try:
            result = self._run_connectivity_test()
        except Exception as e:
            result = f"[连通性测试失败: {e}]"
        # 可扩展为逐步 yield 各阶段结果；当前先整体输出一次
        yield result

    def _run_connectivity_test(self) -> str:
        try:
            from .api_settings_dialog import load_config
        except Exception:
            try:
                from uiLAYER.api_settings_dialog import load_config
            except Exception:
                from api_settings_dialog import load_config
        report_lines: list[str] = []
        # 1) 向量库文件存在性
        idx_exists = Path(self._INDEX_PATH).exists()
        meta_exists = Path(self._META_PATH).exists()
        report_lines.append(f"向量库文件: index={'✓' if idx_exists else '✗'}, meta={'✓' if meta_exists else '✗'}")
        # 2) 本地模型可用性（若存在 models 目录尝试本地加载）
        local_model_dir = Path("models") / "bge-large-zh-v1.5"
        try:
            if local_model_dir.exists():
                from sentence_transformers import SentenceTransformer
                _ = SentenceTransformer(local_model_dir.as_posix())
                report_lines.append("Embedding 模型(本地): ✓ 可加载")
            else:
                report_lines.append("Embedding 模型(本地): 未找到 models/bge-large-zh-v1.5，若离线请预下载")
        except Exception as e:  # 本地加载失败
            report_lines.append(f"Embedding 模型(本地): ✗ 加载失败 - {e}")
        # 3) Hugging Face 可达性（仅网络探测，不强制）
        try:
            resp = requests.get("https://huggingface.co", timeout=3)
            report_lines.append(f"HuggingFace 网络: {'✓' if resp.ok else '✗'} (HTTP {resp.status_code})")
        except Exception as e:
            report_lines.append(f"HuggingFace 网络: ✗ {e}")
        # 4) 当前厂商基础可达性（有 HTTP 响应即视为可达，避免误判）
        cfg = load_config()
        vendor = cfg.get("_meta", {}).get("current_vendor", "OpenAI")
        vendor_cfg = cfg.get(vendor, {})
        base = (vendor_cfg.get("base_url", "") or "").rstrip("/")
        key_present = any(k in vendor_cfg and vendor_cfg[k] for k in ("api_key", "app_id"))

        def _probe(url: str, method: str = "GET", headers: dict | None = None, timeout: int = 6):
            try:
                if method == "HEAD":
                    r = requests.head(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
                elif method == "OPTIONS":
                    r = requests.options(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
                else:
                    r = requests.get(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
                return True, r.status_code
            except Exception as ex:
                return False, str(ex)

        headers = {}
        api_key = vendor_cfg.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # 选择更贴近真实 API 的健康探测端点
        if vendor in ("OpenAI", "DeepSeek", "智谱 ChatGLM"):
            url = f"{base}/v1/models" if base else ""
            ok, status = _probe(url or base or "https://example.com", "GET", headers)
        elif vendor == "阿里通义":
            # DashScope 文本生成端点，用 OPTIONS 以便无需有效负载即可探测
            url = f"{base}/api/v1/services/aigc/text-generation/generation" if base else ""
            ok, status = _probe(url or base or "https://dashscope.aliyuncs.com", "OPTIONS", headers)
        elif vendor == "百度千帆":
            # 直接探测主机可达（HEAD），拿到任意响应即可
            ok, status = _probe(base or "https://qianfan.baidu.com", "HEAD", headers)
        else:
            ok, status = _probe(base, "HEAD", headers)

        if ok:
            report_lines.append(f"{vendor} 基础可达性: ✓ (HTTP {status})，密钥={'已配置' if key_present else '未配置'}")
        else:
            report_lines.append(f"{vendor} 基础可达性: ✗ {status}，密钥={'已配置' if key_present else '未配置'}")
        return "<br/>".join(report_lines)

    # ------------------------------------------------------------------
    # 关闭事件：确保后台线程完全退出
    # ------------------------------------------------------------------
    def closeEvent(self, event):  # type: ignore[override]
        for t in list(self._threads):
            t.quit()
            t.wait()
        # 确保定时器停止
        if hasattr(self, "_thinking_timer"):
            self._thinking_timer.stop()
        super().closeEvent(event)

    def _append_message(self, sender: str, message: str):
        """将消息插入渲染器。统一按 Markdown 渲染，Mermaid 用代码块触发。"""
        is_user = sender.startswith("🧑")
        role = "user" if is_user else "assistant"
        # 统一按 Markdown 渲染
        self._run_js(
            f"window.ChatAPI && ChatAPI.addMessage({json.dumps(role)}, {json.dumps(message)}, true);"
        )

    def _run_js(self, script: str) -> None:
        try:
            if getattr(self, "_page_ready", False):
                page = self.web_view.page()
                if page is not None:
                    # 包装后注入，确保 ChatAPI 可用时才执行
                    def _wrap_js_for_chatapi(raw_script: str) -> str:
                        return (
                            "(function(){\n"
                            "  var __exec = function(){ try { " + raw_script + " } catch(e){} };\n"
                            "  if (window.ChatAPI) { __exec(); } else { setTimeout(__exec, 80); }\n"
                            "})();"
                        )
                    page.runJavaScript(_wrap_js_for_chatapi(script))
            else:
                self._pending_js.append(script)
        except Exception as _:
            if ChatWidget.DEBUG:
                print("[Debug] runJavaScript 执行失败")

    # ------------------------------------------------------------------
    # AI 相关：加载向量库 + 调用大模型（支持流式）
    # ------------------------------------------------------------------
    _INDEX_PATH = "data/manual_faiss.index"
    _META_PATH = "data/manual_meta.pkl"
    _EMBED_MODEL_NAME = "BAAI/bge-large-zh-v1.5"

    def _ensure_retriever(self):
        """
        懒加载向量库、embedding 模型，只在第一次调用时执行，避免拖慢主程序启动。
        添加缓存机制和预加载优化。
        """
        if hasattr(self, "_retriever_ready") and self._retriever_ready:
            return
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            # 先检查索引是否存在，不存在则直接标记不可用，避免无谓加载大模型
            if not Path(self._INDEX_PATH).exists():
                raise FileNotFoundError(f"未找到向量库 {self._INDEX_PATH}，请先运行预处理脚本。")

            # 索引存在时再加载 embedding 模型（可能较慢），减少首调用等待
            local_model_dir = Path("models") / "bge-large-zh-v1.5"
            if local_model_dir.exists():
                self._embed_model = SentenceTransformer(local_model_dir.as_posix())
            else:
                # 正常按名称加载（可能会访问 huggingface.co）
                self._embed_model = SentenceTransformer(self._EMBED_MODEL_NAME)
            
            # 优化FAISS索引加载
            try:
                self._index = faiss.read_index(self._INDEX_PATH)
            except RuntimeError:
                # Windows 中文路径兼容：尝试 8.3 短路径
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes, windll
                    buffer = ctypes.create_unicode_buffer(260)
                    GetShortPathNameW = windll.kernel32.GetShortPathNameW
                    GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
                    GetShortPathNameW.restype = wintypes.DWORD
                    if GetShortPathNameW(self._INDEX_PATH, buffer, 260):
                        short_path = buffer.value
                        self._index = faiss.read_index(short_path)
                    else:
                        raise
                else:
                    raise
            
            # 优化元数据加载
            with open(self._META_PATH, "rb") as f:
                self._chunks = pickle.load(f)
            
            # 预计算一些常用查询的embedding缓存
            self._query_cache = {}
            self._retriever_ready = True
            
            if ChatWidget.DEBUG:
                print("[Debug] 向量检索器加载完成，已启用缓存优化")
                
        except Exception as e:
            # 记录错误，但不要阻塞 UI（允许后续直接调用大模型）
            self._retriever_ready = False
            self._retriever_error = str(e)
            if ChatWidget.DEBUG:
                print(f"[Debug] 向量检索器加载失败: {e}")


    def _is_question_out_of_scope(self, user_text: str) -> bool:
        """
        判断用户问题是否超出多目标水库调度系统的专业范围
        
        Args:
            user_text: 用户输入的问题文本
            
        Returns:
            bool: True表示问题超出范围，False表示问题在范围内
        """
        import re
        
        # 定义系统专业领域的关键词（如果问题包含这些词，通常表示在范围内）
        in_scope_keywords = [
            '水库', '调度', '水利', '水资源', '水文', '流量', '水位', '蓄水',
            '防洪', '发电', '供水', '灌溉', '生态', '环境', '模型', '优化',
            '算法', '参数', '配置', '数据', '分析', '计算', '模拟', '预测',
            '系统', '软件', '界面', '操作', '使用', '设置', '运行', '结果',
            '图表', '可视化', '报告', '输出', '输入', '文件', '导入', '导出'
        ]
        
        # 定义明确超出范围的关键词和模式
        out_of_scope_patterns = [
            # 教育机构（除非与水利工程相关）
            r'\b(大学|学院|学校|高校|教育|学习|课程|专业|学位)\b(?!.*(水利|工程|水库|调度))',
            # 公司企业（除非与水利系统相关）
            r'\b(公司|企业|集团|股份|有限|科技|技术|软件|互联网)\b(?!.*(水利|水库|调度))',
            # 地点位置（除非与水利工程相关）
            r'\b(城市|省份|地区|国家|地址|位置|地图|导航)\b(?!.*(水利|水库|调度))',
            # 人物（除非与水利工程相关）
            r'\b(人物|名人|专家|教授|学者|作者|发明者)\b(?!.*(水利|工程|水库|调度))',
            # 娱乐休闲
            r'\b(游戏|娱乐|电影|音乐|体育|旅游|购物|美食|餐厅)\b',
            # 生活服务
            r'\b(天气|交通|餐饮|住宿|医疗|健康|美容|化妆|服装)\b',
            # 其他非专业领域
            r'\b(政治|经济|文化|历史|艺术|文学|哲学|宗教|法律)\b(?!.*(水利|工程|水库|调度))'
        ]
        
        user_text_lower = user_text.lower()
        
        # 首先检查是否包含专业领域关键词
        has_in_scope_keywords = any(keyword in user_text_lower for keyword in in_scope_keywords)
        
        # 检查是否包含超出范围的关键词（使用负向前瞻避免误判）
        has_out_of_scope_keywords = False
        for pattern in out_of_scope_patterns:
            if re.search(pattern, user_text_lower):
                has_out_of_scope_keywords = True
                break
        
        # 检查是否包含特定的外部实体名称（如"长安大学"）
        external_entities = [
            '长安大学', '清华大学', '北京大学', '浙江大学', '复旦大学', '同济大学',
            '百度', '腾讯', '阿里巴巴', '华为', '小米', '京东', '美团',
            '北京', '上海', '广州', '深圳', '杭州', '南京', '武汉', '成都'
        ]
        
        has_external_entities = any(entity in user_text for entity in external_entities)
        
        # 判断逻辑：
        # 1. 如果包含外部实体且不包含专业关键词，则超出范围
        # 2. 如果包含超出范围关键词且不包含专业关键词，则超出范围
        # 3. 如果同时包含专业关键词和外部实体，需要进一步判断
        
        if has_external_entities and not has_in_scope_keywords:
            return True
        
        if has_out_of_scope_keywords and not has_in_scope_keywords:
            return True
        
        # 特殊处理：如果问题很短且只包含外部实体名称，直接拒绝
        if len(user_text.strip()) <= 10 and has_external_entities:
            return True
        
        return False

    def _stream_ai_reply(self, user_text: str) -> Iterator[str]:
        """
        与 _get_ai_reply 逻辑一致，但尽可能走流式接口；若不支持，则作为一次性完整结果产出一次。
        """
        # 0) 首先检查问题是否超出专业范围
        if self._is_question_out_of_scope(user_text):
            # 直接返回拒绝回答的格式
            rejection_response = (
                "抱歉，我在手册中没有找到相关信息。\n\n"
                "以下内容基于我的理解和推测，仅供参考：\n"
                "您询问的内容与多目标水库调度系统的专业领域无关。本系统专注于水库调度、水利工程、水资源管理等相关问题。\n\n"
                "（注：根据规则1，系统助手应拒绝回答非专业领域问题。本回答仅作格式示范，实际使用中应严格限定回答范围）"
            )
            yield rejection_response
            return
        
        # 1) 向量检索与 Prompt 组装
        # 检查是否启用用户手册查看
        use_manual = getattr(self, "cb_use_manual", None) and self.cb_use_manual.isChecked()
        
        if use_manual:
            self._ensure_retriever()
            retriever_ok = getattr(self, "_retriever_ready", False)
        else:
            retriever_ok = False  # 不查看手册时跳过向量检索
        try:
            from .api_settings_dialog import load_config
        except Exception:
            try:
                from uiLAYER.api_settings_dialog import load_config
            except Exception:
                from api_settings_dialog import load_config
        context_text = ""
        if retriever_ok:
            # 使用缓存优化查询
            if user_text in getattr(self, '_query_cache', {}):
                context_text = self._query_cache[user_text]
                if ChatWidget.DEBUG:
                    print("[Debug] 使用缓存的向量检索结果")
            else:
                # 优化embedding计算
                q_emb = self._embed_model.encode([user_text], normalize_embeddings=True)
                D, I = self._index.search(q_emb, k=5)  # 增加检索数量以获取更多相关内容
                context_parts = []
                used_sections = set()  # 避免重复章节
                
                for score, idx in zip(D[0], I[0]):
                    if score < 0.25:  # 降低相似度阈值以获取更多相关内容
                        continue
                    
                    chunk = self._chunks[idx]
                    
                    # 检查是否是增强格式的文本块
                    if isinstance(chunk, dict) and 'display_text' in chunk:
                        # 新格式：使用增强的显示文本
                        section_title = chunk.get('section_title', '')
                        if section_title not in used_sections:
                            context_parts.append(chunk['display_text'])
                            used_sections.add(section_title)
                    else:
                        # 旧格式：直接使用文本内容
                        context_parts.append(chunk)
                
                context_text = "\n\n---\n\n".join(context_parts) if context_parts else "（未检索到相关内容）"
                
                # 缓存结果（限制缓存大小）
                if hasattr(self, '_query_cache'):
                    if len(self._query_cache) > 50:  # 限制缓存大小
                        # 清除最旧的缓存
                        oldest_key = next(iter(self._query_cache))
                        del self._query_cache[oldest_key]
                    self._query_cache[user_text] = context_text
        # 构建基础系统提示词
        system_prompt = (
            "你是多目标水库调度系统的专业帮助助手。请严格遵循以下回答规则：\n\n"
            "1. **严格拒绝回答范围**：\n"
            "   - 拒绝回答与多目标水库调度系统完全无关的外部实体信息（如学校、公司、地点、人物等）\n"
            "   - 拒绝回答与系统功能无关的软件使用问题和要求\n"
            "   - 拒绝回答非学术、非专业的问题和要求\n"
            "   - 拒绝回答超出系统专业领域的问题\n"
            "   - 拒绝回答与水库调度、水利工程、水资源管理无关的问题\n\n"
            "2. **信息判断标准**：\n"
            "   - 如果手册中包含了与用户问题直接相关的具体操作步骤、功能说明或配置方法，则视为找到了相关信息\n"
            "   - 如果手册中只有间接相关或过于宽泛的内容，且无法提供具体的操作指导，则视为未找到相关信息\n"
            "   - 如果问题涉及外部实体、非系统相关内容，直接拒绝回答\n\n"
            "3. **拒绝回答格式**：当遇到与系统无关的问题时，必须按以下格式回答：\n"
            "   - 首先明确说明：'抱歉，我在手册中没有找到相关信息。'\n"
            "   - 然后说明：'以下内容基于我的理解和推测，仅供参考：'\n"
            "   - 最后提供基于常识的推测性回答\n"
            "   - 在回答末尾添加：'（注：根据规则1，系统助手应拒绝回答非专业领域问题。本回答仅作格式示范，实际使用中应严格限定回答范围）'\n\n"
            "4. **回答格式**：用中文、简明、结构化的方式回答\n"
            "5. **专业范围**：专注于多目标水库调度系统的使用、配置、优化等相关问题\n"
            "6. **优先级**：当用户问题明显超出专业范围时，优先执行拒绝回答机制\n\n"
        )
        
        if retriever_ok:
            prompt = (
                f"{system_prompt}"
                "你是多目标水库调度系统的帮助助手，基于以下手册摘录回答用户问题：\n"
                "-----\n"
                f"{context_text}\n"
                "-----\n"
                f"用户问题：{user_text}\n"
                "请严格按照上述规则回答。"
            )
        else:
            prompt = (
                f"{system_prompt}"
                "你是多目标水库调度系统的帮助助手，当前未加载向量检索，请基于常识与已知上下文直接回答用户问题。\n"
                f"用户问题：{user_text}\n"
                "请严格按照上述规则回答。"
            )
        if getattr(self, "cb_show_thoughts", None) and self.cb_show_thoughts.isChecked():
            thinking_prefix = (
                "请严格按照如下格式输出，先给出推理再给出答案（若有引用请简要列出）：\n"
                "思考：<在此给出详细推理过程、关键假设和中间步骤>\n"
                "答案：<在此给出最终简明答案>\n"
            )
            prompt = thinking_prefix + "\n" + prompt

        # 根据配置决定是否包含mermaid指令
        from config.performance_manager import performance_manager
        
        style_guide = (
            "\n回答规范：\n"
            "- 使用 Markdown 格式\n"
            "- 数学公式用 LaTeX：行内 $...$，多行 $$...$$\n"
            "- 简明扼要，重点突出\n"
        )
        
        # 如果启用了mermaid生成，添加相关指令
        if performance_manager.is_mermaid_generation_enabled():
            style_guide += (
                "- 在解释复杂流程、系统架构、数据流向时，请使用 Mermaid 图表\n"
                "- 支持流程图 (flowchart)、时序图 (sequenceDiagram)、类图 (classDiagram) 等\n"
                "- 图表代码块格式：```mermaid\n图表代码\n```\n"
            )
        
        prompt = prompt + "\n\n" + style_guide

        # 2) 厂商选择与流式调用
        cfg = load_config()
        vendor_raw = cfg.get("_meta", {}).get("current_vendor", "OpenAI")
        _alias = {
            "阿里通义": "阿里通义",
            "通义千问": "阿里通义",
            "千问": "阿里通义",
            "DeepSeek": "DeepSeek",
            "百度千帆": "百度千帆",
            "OpenAI": "OpenAI",
        }
        vendor = _alias.get(vendor_raw, vendor_raw)
        try:
            if vendor == "OpenAI":
                _cred = cfg.get("OpenAI", {})
                _yielded = False
                for part in self._stream_openai(prompt, _cred):
                    _yielded = True
                    yield part
                if not _yielded:
                    # 无分片回退为一次性
                    yield self._call_openai(prompt, _cred)
            elif vendor == "DeepSeek":
                _cred = cfg.get("DeepSeek", {})
                _yielded = False
                for part in self._stream_deepseek(prompt, _cred):
                    _yielded = True
                    yield part
                if not _yielded:
                    yield self._call_deepseek(prompt, _cred)
            elif vendor == "百度千帆":
                # 暂无流式，退化为一次性
                yield self._call_qianfan(prompt, cfg.get("百度千帆", {}))
            elif vendor == "阿里通义":
                _cred = cfg.get("阿里通义", {})
                _yielded = False
                for part in self._stream_tongyi(prompt, _cred):
                    _yielded = True
                    yield part
                if not _yielded:
                    # SSE 未返回增量时，回退非流式
                    yield self._call_tongyi(prompt, _cred)
            else:
                yield f"[暂不支持的厂商: {vendor_raw}]"
        except Exception as e:
            yield f"[调用 {vendor} 失败: {e}]"

    # ------------------------------------------------------------------
    # UI 辅助：折叠/展开与"正在思考"动画
    # ------------------------------------------------------------------
    def _toggle_collapsed(self) -> None:
        self._collapsed = not self._collapsed
        # 隐藏/显示聊天记录与输入区
        self.web_view.setVisible(not self._collapsed)
        self.input_container.setVisible(not self._collapsed)
        # 思考条仅在未折叠时可见
        self.thinking_label.setVisible(not self._collapsed and self.thinking_label.isVisible())
        # 切换按钮外观轻微反馈
        self.btn_collapse.setText("▮" if self._collapsed else "▍")

    def _start_thinking_animation(self) -> None:
        if self._collapsed:
            # 折叠状态不显示动画
            return
        self.thinking_label.show()
        self._thinking_frame = 0
        if not self._thinking_timer.isActive():
            self._thinking_timer.start()

    def _stop_thinking_animation(self) -> None:
        self._thinking_timer.stop()
        self.thinking_label.hide()

    def _update_thinking_animation(self) -> None:
        """更新思考动画帧。"""
        if self._thinking_frame >= len(self._thinking_chars):
            self._thinking_frame = 0
        self.thinking_label.setText(self._thinking_chars[self._thinking_frame])
        self._thinking_frame += 1

    def show_system_report(self, report_type: str, content: str, title: str = ""):
        """
        显示系统生成的报告（模型运行报告、调度优化报告等）
        
        Args:
            report_type: 报告类型，如 'model_run', 'schedule_optimization'
            content: 报告内容（Markdown格式）
            title: 报告标题，如果为空字符串则使用默认标题
        """
        if not title:
            if report_type == 'model_run':
                title = "🤖 模型运行报告"
            elif report_type == 'schedule_optimization':
                title = "📊 调度优化报告"
            else:
                title = "📋 系统报告"
        
        # 在聊天界面中显示报告
        self._append_message("🤖 系统助手", f"**{title}**\n\n{content}")
        
        # 自动滚动到底部
        self._run_js("window.ChatAPI && ChatAPI.scrollToBottom();")

    def show_model_run_report(self, model_name: str, reservoir_results: dict, params: dict, failures: dict | None = None):
        """
        生成并显示模型运行报告
        
        Args:
            model_name: 模型名称
            reservoir_results: 水库结果字典
            params: 模型参数
        """
        report_lines = []
        report_lines.append(f"## 📊 {model_name} 模型运行报告")
        report_lines.append("")
        
        # 基本信息
        report_lines.append("### 基本信息")
        report_lines.append(f"- **模型名称**: {model_name}")
        report_lines.append(f"- **运行时间**: {self._get_current_time()}")
        report_lines.append(f"- **水库数量**: {len(reservoir_results)}")
        report_lines.append("")
        
        # 模型参数
        report_lines.append("### 模型参数")
        for key, value in params.items():
            report_lines.append(f"- **{key}**: {value}")
        report_lines.append("")
        
        # 各水库运行结果
        report_lines.append("### 水库运行结果")
        for reservoir_id, results in reservoir_results.items():
            report_lines.append(f"#### 水库 {reservoir_id}")
            if results is not None and hasattr(results, 'empty') and not results.empty:
                report_lines.append(f"- **状态**: ✅ 运行成功")
                report_lines.append(f"- **数据行数**: {len(results)}")
                report_lines.append(f"- **数据列数**: {len(results.columns)}")
                if 'reservoir_id' in results.columns:
                    report_lines.append(f"- **水库ID**: {results['reservoir_id'].iloc[0]}")
            else:
                report_lines.append(f"- **状态**: ❌ 运行失败")
            report_lines.append("")
        
        # 失败详情（若有）
        if failures:
            report_lines.append("### 失败详情")
            for rid, info in failures.items():
                reason = info.get('message') if isinstance(info, dict) else str(info)
                diag = info.get('diagnostics') if isinstance(info, dict) else None
                report_lines.append(f"- **水库 {rid}**: {reason}")
                if isinstance(diag, dict) and diag.get('first_invalid'):
                    fi = diag['first_invalid']
                    report_lines.append(f"  - 首次异常位置: t={fi.get('time_index')}, x={fi.get('space_index')}")
                report_lines.append("")
        
        # 总结
        total_count = len(reservoir_results) + (len(failures) if failures else 0)
        success_count = sum(1 for r in reservoir_results.values() if r is not None and hasattr(r, 'empty') and not r.empty)
        report_lines.append("### 运行总结")
        report_lines.append(f"- **总水库数**: {total_count}")
        report_lines.append(f"- **成功运行**: {success_count}")
        fail_count = total_count - success_count
        report_lines.append(f"- **失败数量**: {fail_count}")
        if total_count > 0:
            report_lines.append(f"- **成功率**: {success_count/total_count*100:.1f}%")
        
        report_content = "\n".join(report_lines)
        self.show_system_report('model_run', report_content)

    def show_schedule_optimization_report(self, objectives: dict, params: dict, results: dict):
        """
        生成并显示调度优化报告
        
        Args:
            objectives: 优化目标字典
            params: 算法参数
            results: 优化结果
        """
        report_lines = []
        report_lines.append("## 🎯 调度优化报告")
        report_lines.append("")
        
        # 基本信息
        report_lines.append("### 基本信息")
        report_lines.append(f"- **运行时间**: {self._get_current_time()}")
        report_lines.append(f"- **优化算法**: NSGA-III")
        report_lines.append("")
        
        # 优化目标
        report_lines.append("### 优化目标")
        active_objectives = [obj for obj, active in objectives.items() if active]
        for obj in active_objectives:
            if obj == 'flood':
                report_lines.append("- **防洪目标**: 最小化最大下泄流量占允许值的比例")
            elif obj == 'power':
                report_lines.append("- **发电目标**: 最大化累计发电量")
            elif obj == 'supply':
                report_lines.append("- **供水目标**: 最小化供水缺口比例")
            elif obj == 'ecology':
                report_lines.append("- **生态目标**: 最小化不满足生态基流的时段比例")
        report_lines.append("")
        
        # 算法参数
        report_lines.append("### 算法参数")
        for key, value in params.items():
            report_lines.append(f"- **{key}**: {value}")
        report_lines.append("")
        
        # 优化结果
        if results and 'optimization_results' in results:
            opt_results = results['optimization_results']
            if not opt_results.empty:
                report_lines.append("### 优化结果")
                report_lines.append(f"- **帕累托解数量**: {len(opt_results)}")
                report_lines.append(f"- **水库数量**: {opt_results.get('reservoir_id', pd.Series()).nunique() if 'reservoir_id' in opt_results.columns else '未知'}")
                
                # 目标函数值范围
                if 'flood' in opt_results.columns:
                    flood_range = f"{opt_results['flood'].min():.4f} - {opt_results['flood'].max():.4f}"
                    report_lines.append(f"- **防洪目标范围**: {flood_range}")
                if 'power' in opt_results.columns:
                    power_range = f"{opt_results['power'].min():.4f} - {opt_results['power'].max():.4f}"
                    report_lines.append(f"- **发电目标范围**: {power_range}")
                if 'supply' in opt_results.columns:
                    supply_range = f"{opt_results['supply'].min():.4f} - {opt_results['supply'].max():.4f}"
                    report_lines.append(f"- **供水目标范围**: {supply_range}")
                if 'ecology' in opt_results.columns:
                    ecology_range = f"{opt_results['ecology'].min():.4f} - {opt_results['ecology'].max():.4f}"
                    report_lines.append(f"- **生态目标范围**: {ecology_range}")
                
                report_lines.append("")
        
        # 调度策略信息
        if results and 'schedule_strategy' in results:
            strategy = results['schedule_strategy']
            if strategy:
                report_lines.append("### 调度策略建议")
                summary = strategy.get('summary', {})
                report_lines.append(f"- **总水库数**: {summary.get('total_reservoirs', 0)}")
                report_lines.append(f"- **活跃目标**: {', '.join(summary.get('active_objectives', []))}")
                report_lines.append(f"- **帕累托解总数**: {summary.get('total_pareto_solutions', 0)}")
                
                # 水库策略
                reservoir_strategies = strategy.get('reservoir_strategies', [])
                for strategy_info in reservoir_strategies:
                    res_id = strategy_info.get('reservoir_id', 0)
                    report_lines.append(f"\n#### 水库 {res_id} 策略")
                    report_lines.append(f"- **帕累托解数量**: {strategy_info.get('pareto_solutions_count', 0)}")
                    
                    recommendations = strategy_info.get('recommended_strategies', [])
                    for i, rec in enumerate(recommendations[:3], 1):  # 只显示前3个建议
                        report_lines.append(f"- **建议{i}**: {rec.get('description', '')}")
                        if 'objective_values' in rec:
                            obj_values = rec['objective_values']
                            report_lines.append(f"  - 目标值: {obj_values}")
        
        report_content = "\n".join(report_lines)
        self.show_system_report('schedule_optimization', report_content)

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # 各厂商调用实现
    # ------------------------------------------------------------------
    def _call_openai(self, prompt: str, cred: dict) -> str:
        # 检查缓存
        cached_response = performance_manager.get_cached_response(prompt)
        if cached_response:
            return cached_response
        
        # 开始计时
        start_time = performance_manager.start_timer()
        
        try:
            import openai
            openai.api_key = cred.get("api_key") or os.getenv("OPENAI_API_KEY", "")
            
            # 使用性能配置
            temperature = performance_manager.get_model_setting("temperature", 0.2)
            base_max_tokens = performance_manager.get_model_setting("max_tokens", 2000)
            
            # 检查长文本模式
            long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
            if long_text_mode:
                max_tokens = base_max_tokens * 3  # 长文本模式使用3倍token
                # 在提示词中添加长文本要求
                prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
            else:
                max_tokens = base_max_tokens
            
            resp = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response = resp.choices[0].message.content.strip()
            
            # 缓存响应
            performance_manager.cache_response(prompt, response)
            
            return response
        finally:
            # 结束计时
            performance_manager.end_timer(start_time, "OpenAI调用")

    def _stream_openai(self, prompt: str, cred: dict) -> Iterator[str]:
        """OpenAI ChatCompletion 流式输出（兼容 openai<1.0 的旧SDK）。"""
        # 开始计时
        start_time = performance_manager.start_timer()
        
        try:
            import openai
            openai.api_key = cred.get("api_key") or os.getenv("OPENAI_API_KEY", "")
            
            # 使用性能配置
            temperature = performance_manager.get_model_setting("temperature", 0.2)
            base_max_tokens = performance_manager.get_model_setting("max_tokens", 2000)
            
            # 检查长文本模式
            long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
            if long_text_mode:
                max_tokens = base_max_tokens * 3  # 长文本模式使用3倍token
                # 在提示词中添加长文本要求
                prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
            else:
                max_tokens = base_max_tokens
            
            stream = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                model=cred.get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            response_parts = []
            for event in stream:
                try:
                    delta = event["choices"][0]["delta"]
                    content = delta.get("content")
                    if content:
                        response_parts.append(content)
                        yield content
                except Exception:
                    continue
            
            # 缓存完整响应
            full_response = "".join(response_parts)
            if full_response:
                performance_manager.cache_response(prompt, full_response)
                
        finally:
            # 结束计时
            performance_manager.end_timer(start_time, "OpenAI流式调用")

    def _call_qianfan(self, prompt: str, cred: dict) -> str:
        """百度千帆 ERNIE-Bot-turbo 简化版 REST 调用。"""
        api_key = cred.get("api_key")
        secret_key = cred.get("secret_key")
        base_url = cred.get("base_url", "https://aip.baidubce.com")
        if not api_key or not secret_key:
            raise ValueError("请先在 API 设置中填写百度千帆 api_key / secret_key")
        # 获取 access_token（简单缓存到实例变量）
        if not hasattr(self, "_qianfan_token"):
            token_url = f"{base_url}/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key,
            }
            token_resp = requests.get(token_url, params=params, timeout=10).json()
            if "access_token" not in token_resp:
                raise RuntimeError(token_resp.get("error_description", "获取 access_token 失败"))
            self._qianfan_token = token_resp["access_token"]
        chat_url = f"{base_url}/rpc/2.0/ai_custom/v1/chat/completions?access_token={self._qianfan_token}"
        
        # 检查长文本模式
        long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
        if long_text_mode:
            # 在提示词中添加长文本要求
            prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
        
        payload = {
            "model": "ERNIE-Bot-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        resp = requests.post(chat_url, json=payload, timeout=20).json()
        if resp.get("error_code", 0) != 0:
            raise RuntimeError(resp.get("error_msg", "调用失败"))
        return resp["result"]

    def _call_tongyi(self, prompt: str, cred: dict) -> str:
        """阿里通义 DashScope 简化版 REST 调用。"""
        api_key = cred.get("api_key")
        if not api_key:
            raise ValueError("请先在 API 设置中填写阿里通义 api_key")
        base = cred.get("base_url", "https://dashscope.aliyuncs.com").rstrip("/")
        url = base + "/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # 默认使用 qwen-flash，用户可在配置中覆盖
        model_name = cred.get("model", "qwen-flash")
        
        # 检查长文本模式
        long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
        if long_text_mode:
            # 在提示词中添加长文本要求
            prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
        
        payload = {
            "model": model_name,
            "input": {"prompt": prompt},
            "parameters": {"temperature": 0.2},
        }
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        try:
            resp = response.json()
        except Exception:
            raise RuntimeError(f"非 JSON 响应，HTTP {response.status_code}: {response.text[:200]}")
        # DashScope 若失败通常包含 code/message 字段
        if isinstance(resp, dict) and resp.get("code"):
            raise RuntimeError(resp.get("message", "调用失败"))
        # 成功时 output 可能为字符串或对象
        output = resp.get("output") if isinstance(resp, dict) else None
        if isinstance(output, dict):
            text = output.get("text") or output.get("answer")
        else:
            text = output
        if not text and "choices" in resp:
            # 兼容 OpenAI 格式
            try:
                text = resp["choices"][0]["message"]["content"]
            except Exception:
                pass
        if not text:
            raise RuntimeError(f"未从响应中解析到文本: {str(resp)[:200]}")
        return str(text).strip()

    def _stream_tongyi(self, prompt: str, cred: dict) -> Iterator[str]:
        """阿里通义 DashScope 文本生成 SSE 流式输出。

        注意：
        - 不伪造模型内容。若勾选"显示思考"，仅在流式开始处插入一次分隔标记（UI 提示用），
          实际的"思考/答案"需由提示词引导模型自行生成（见 _stream_ai_reply 中的 thinking_prefix）。
        """
        api_key = cred.get("api_key")
        if not api_key:
            raise ValueError("请先在 API 设置中填写阿里通义 api_key")
        base = cred.get("base_url", "https://dashscope.aliyuncs.com")
        url = base.rstrip("/") + "/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-DashScope-SSE": "enable",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        model_name = cred.get("model", "qwen-flash")
        
        # 检查长文本模式
        long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
        if long_text_mode:
            # 在提示词中添加长文本要求
            prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
        
        payload = {
            "model": model_name,
            "input": {"prompt": prompt},
            "parameters": {"temperature": 0.2},
            "stream": True,
            "incremental_output": True,
        }
        
        # 获取配置的流式块大小
        chunk_size = performance_manager.get_performance_setting("stream_chunk_size", 5)
        text_buffer = ""  # 用于累积文本
        
        if ChatWidget.DEBUG:
            print(f"[Debug] 通义千问流式分块大小: {chunk_size}")
        
        with requests.post(url, json=payload, headers=headers, timeout=(6, 60), stream=True) as r:
            r.raise_for_status()
            # 若用户勾选"显示思考"，在首个有效分片前输出一次提示性分隔标记（不包含任何伪造思考内容）
            inserted_thought_banner = False
            for raw_line in r.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if raw_line.startswith("data: "):
                    data = raw_line[6:].strip()
                    if data == "[DONE]":
                        # 输出剩余的缓冲区内容
                        if text_buffer:
                            yield text_buffer
                        break
                    try:
                        obj = json.loads(data)
                    except Exception as e:
                        if ChatWidget.DEBUG:
                            print(f"[Debug] 通义千问流式解析错误: {e}")
                        continue
                    # 通义常见结束标识也可能包含在对象内
                    if isinstance(obj, dict) and obj.get("is_end") is True:
                        # 输出剩余的缓冲区内容
                        if text_buffer:
                            yield text_buffer
                        break
                    # 常见返回：{"output": {"text": "..."}, "is_end": false, ...}
                    text = None
                    output = obj.get("output") if isinstance(obj, dict) else None
                    if isinstance(output, dict):
                        # 优先增量字段
                        text = output.get("text") or output.get("delta") or output.get("answer")
                    if text is None and isinstance(obj, dict) and "choices" in obj:
                        try:
                            text = obj["choices"][0]["delta"]["content"]
                        except Exception:
                            try:
                                text = obj["choices"][0]["message"]["content"]
                            except Exception:
                                text = None
                    if text:
                        if (not inserted_thought_banner) and getattr(self, "cb_show_thoughts", None) and self.cb_show_thoughts.isChecked():
                            # UI 分隔标记：提示后续为"思考/答案"两段输出，由提示词引导模型生成实际内容
                            yield "\n" + "=" * 48 + "\n思考过程：\n" + "=" * 48 + "\n"
                            inserted_thought_banner = True
                        
                        # 将新内容添加到缓冲区
                        text_str = str(text)
                        text_buffer += text_str
                        
                        # 当缓冲区达到或超过块大小时，输出分块
                        while len(text_buffer) >= chunk_size:
                            yield text_buffer[:chunk_size]
                            text_buffer = text_buffer[chunk_size:]
            
            # 输出剩余的缓冲区内容
            if text_buffer:
                yield text_buffer

    def _call_deepseek(self, prompt: str, cred: dict) -> str:
        """DeepSeek Chat API 调用（OpenAI 兼容）。"""
        api_key = cred.get("api_key")
        if not api_key:
            raise ValueError("请先在 API 设置中填写 DeepSeek api_key")
        base = cred.get("base_url", "https://api.deepseek.com")
        url = base.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # 检查长文本模式
        long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
        if long_text_mode:
            # 在提示词中添加长文本要求
            prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
        
        payload = {
            "model": cred.get("model", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=20).json()
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message", "调用失败"))
        return resp["choices"][0]["message"]["content"].strip()

    def _stream_deepseek(self, prompt: str, cred: dict) -> Iterator[str]:
        """DeepSeek 流式输出（SSE，OpenAI 兼容）。"""
        api_key = cred.get("api_key")
        if not api_key:
            raise ValueError("请先在 API 设置中填写 DeepSeek api_key")
        base = cred.get("base_url", "https://api.deepseek.com")
        url = base.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        # 检查长文本模式
        long_text_mode = getattr(self, "cb_long_text_mode", None) and self.cb_long_text_mode.isChecked()
        if long_text_mode:
            # 在提示词中添加长文本要求
            prompt += "\n\n注意：请提供详细回答，至少输出500字文本，包含具体的操作步骤、注意事项和最佳实践。"
        
        payload = {
            "model": cred.get("model", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": True,
        }
        
        # 获取配置的流式块大小
        chunk_size = performance_manager.get_performance_setting("stream_chunk_size", 5)
        text_buffer = ""  # 用于累积文本
        
        if ChatWidget.DEBUG:
            print(f"[Debug] DeepSeek流式分块大小: {chunk_size}")
        
        with requests.post(url, json=payload, headers=headers, timeout=(6, 60), stream=True) as r:
            r.raise_for_status()
            for raw_line in r.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if raw_line.startswith("data: "):
                    data = raw_line[6:].strip()
                    if data == "[DONE]":
                        # 输出剩余的缓冲区内容
                        if text_buffer:
                            yield text_buffer
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"]
                        content = delta.get("content")
                        if content:
                            # 将新内容添加到缓冲区
                            text_buffer += content
                            
                            # 当缓冲区达到或超过块大小时，输出分块
                            while len(text_buffer) >= chunk_size:
                                yield text_buffer[:chunk_size]
                                text_buffer = text_buffer[chunk_size:]
                                
                    except Exception as e:
                        if ChatWidget.DEBUG:
                            print(f"[Debug] DeepSeek流式解析错误: {e}")
                        continue
            
            # 输出剩余的缓冲区内容
            if text_buffer:
                yield text_buffer

    # ------------------------------------------------------------------
    # API选择相关方法
    # ------------------------------------------------------------------
    def _load_api_options(self):
        """加载API选项到下拉框"""
        try:
            # 只显示已配置API密钥的厂商
            vendor_names = get_configured_vendors()
            
            # 清空并重新添加选项
            self.api_combo.clear()
            
            if vendor_names:
                self.api_combo.addItems(vendor_names)
                
                # 设置当前选中的API
                config = load_config()
                current_vendor = config.get("_meta", {}).get("current_vendor", "OpenAI")
                if current_vendor in vendor_names:
                    self.api_combo.setCurrentText(current_vendor)
                else:
                    self.api_combo.setCurrentText(vendor_names[0])
            else:
                # 如果没有配置任何API，显示提示信息
                self.api_combo.addItem("请先配置API")
                
        except Exception as e:
            if ChatWidget.DEBUG:
                print(f"[Debug] 加载API选项失败: {e}")
            # 添加默认选项
            self.api_combo.clear()
            self.api_combo.addItem("请先配置API")

    def _on_api_changed(self, vendor: str):
        """当API选择改变时更新配置"""
        # 如果选择的是提示信息，不更新配置
        if vendor == "请先配置API":
            return
            
        try:
            config = load_config()
            # 更新当前选中的厂商
            config.setdefault("_meta", {})["current_vendor"] = vendor
            
            # 保存配置
            from .api_settings_dialog import save_config
            save_config(config)
            
            if ChatWidget.DEBUG:
                print(f"[Debug] API已切换到: {vendor}")
                
        except Exception as e:
            if ChatWidget.DEBUG:
                print(f"[Debug] 切换API失败: {e}")

    def refresh_api_options(self):
        """刷新API选项（供外部调用）"""
        self._load_api_options()