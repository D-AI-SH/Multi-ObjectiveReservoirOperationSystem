from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
    QWidget,
    QFormLayout,
)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

CONFIG_FILE = Path("config/api_keys.json")
DEFAULT_VENDORS = {
    "OpenAI": {"api_key": "", "base_url": "https://api.openai.com"},
    "百度千帆": {"api_key": "", "secret_key": "", "base_url": "https://qianfan.baidu.com"},
    "阿里通义": {"api_key": "", "base_url": "https://dashscope.aliyuncs.com", "model": "qwen-flash"},
    "讯飞星火": {"app_id": "", "api_key": "", "api_secret": "", "base_url": "https://spark-api.xf-yun.com"},
    "智谱 ChatGLM": {"api_key": "", "base_url": "https://open.bigmodel.cn"},
    "MiniMax": {"group_id": "", "api_key": "", "base_url": "https://api.minimax.chat"},
    "DeepSeek": {"api_key": "", "base_url": "https://api.deepseek.com"},
    "硅基流动": {"api_key": "", "base_url": "https://platform.ai-siliconflow.com"},
    "月之暗面": {"api_key": "", "base_url": "https://api.moonshot-ai.com"},
}

# 各厂商的API购买页面链接
VENDOR_PURCHASE_URLS = {
    "OpenAI": "https://platform.openai.com/api-keys",
    "百度千帆": "https://console.bce.baidu.com/qianfan/overview",
    "阿里通义": "https://dashscope.console.aliyun.com/apiKey",
    "讯飞星火": "https://console.xfyun.cn/services/spark",
    "智谱 ChatGLM": "https://open.bigmodel.cn/usercenter/apikeys",
    "MiniMax": "https://api.minimax.chat/console/app",
    "DeepSeek": "https://platform.deepseek.com/api_keys",
    "硅基流动": "https://platform.ai-siliconflow.com/console",
    "月之暗面": "https://platform.moonshot.cn/console/api-keys",
}


def load_config() -> Dict[str, Dict[str, str]]:
    """加载配置文件并与默认厂商合并。"""
    data: Dict[str, Dict[str, str]] = DEFAULT_VENDORS.copy()
    if CONFIG_FILE.exists():
        try:
            file_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # 合并，已有字段保留用户输入
            for vendor, fields in file_data.items():
                if vendor not in data:
                    data[vendor] = fields
                else:
                    data[vendor].update(fields)
        except Exception:
            pass
    return data


def get_configured_vendors() -> list[str]:
    """获取已配置API密钥的厂商列表。"""
    config = load_config()
    configured_vendors = []
    
    for vendor, fields in config.items():
        if vendor.startswith("_"):  # 跳过内部键
            continue
            
        # 检查是否有API密钥配置
        has_api_key = False
        for key, value in fields.items():
            if any(keyword in key.lower() for keyword in ["api_key", "secret_key", "app_id", "group_id"]):
                if value and value.strip():
                    has_api_key = True
                    break
        
        if has_api_key:
            configured_vendors.append(vendor)
    
    return configured_vendors


def save_config(data: Dict[str, Dict[str, str]]):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ApiSettingsDialog(QDialog):
    """API 配置对话框。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("API 配置")
        self.resize(400, 250)

        self._config = load_config()
        # 当前默认厂商
        self._current_vendor = self._config.get("_meta", {}).get("current_vendor", "OpenAI")
        self._init_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 选择厂商
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("选择厂商："))
        self.vendor_combo = QComboBox()
        # 只显示真正的厂商（排除 _ 前缀的内部键）
        self._vendor_names = [k for k in self._config.keys() if not k.startswith("_")]
        self.vendor_combo.addItems(self._vendor_names)
        self.vendor_combo.setCurrentText(self._current_vendor)
        self.vendor_combo.currentTextChanged.connect(self._on_vendor_changed)
        top_layout.addWidget(self.vendor_combo)
        
        # 添加获取密钥按钮
        self.btn_get_key = QPushButton("获取密钥")
        self.btn_get_key.clicked.connect(self._on_get_key)
        top_layout.addWidget(self.btn_get_key)
        
        main_layout.addLayout(top_layout)

        # 表单区
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        main_layout.addWidget(self.form_widget)

        # 保存 / 取消 / 测试连接
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("测试连接")
        self.btn_test.clicked.connect(self._on_test)
        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        # 初始化表单
        self._on_vendor_changed(self.vendor_combo.currentText())

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def _on_get_key(self):
        """打开当前选中厂商的API购买页面"""
        vendor = self.vendor_combo.currentText()
        if vendor in VENDOR_PURCHASE_URLS:
            url = VENDOR_PURCHASE_URLS[vendor]
            try:
                QDesktopServices.openUrl(QUrl(url))
                QMessageBox.information(self, "已打开", f"已在浏览器中打开 {vendor} 的API密钥获取页面")
            except Exception as e:
                QMessageBox.warning(self, "打开失败", f"无法打开浏览器：{e}")
        else:
            QMessageBox.warning(self, "未知厂商", f"未找到 {vendor} 的API购买页面")

    def _on_vendor_changed(self, vendor: str):
        # 清空现有表单
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self._edit_lines: Dict[str, QLineEdit] = {}

        fields = self._config[vendor]
        for key, val in fields.items():
            line = QLineEdit(val)
            line.setEchoMode(QLineEdit.EchoMode.Password if "key" in key.lower() or "secret" in key.lower() else QLineEdit.EchoMode.Normal)
            self.form_layout.addRow(QLabel(key), line)
            self._edit_lines[key] = line

    def _on_save(self):
        vendor = self.vendor_combo.currentText()
        for key, line in self._edit_lines.items():
            self._config[vendor][key] = line.text().strip()
        # 记录当前选择的厂商
        self._config.setdefault("_meta", {})["current_vendor"] = vendor
        save_config(self._config)
        QMessageBox.information(self, "已保存", f"{vendor} 配置已保存。")
        
        # 通知父窗口刷新API选项（如果父窗口是聊天助手）
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'refresh_api_options'):
                parent.refresh_api_options()  # type: ignore
        except Exception:
            pass  # 忽略刷新失败
        
        self.accept()

    def _on_test(self):
        import requests
        vendor = self.vendor_combo.currentText()
        # 临时构造提交体用于测试
        temp_cfg = {k: line.text().strip() for k, line in self._edit_lines.items()}
        base = temp_cfg.get("base_url", "").rstrip("/")

        def _probe(url: str, method: str = "GET", headers: dict | None = None, timeout: int = 6):
            try:
                if method == "HEAD":
                    r = requests.head(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
                elif method == "OPTIONS":
                    r = requests.options(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
                else:
                    r = requests.get(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
                return True, r
            except Exception as ex:
                return False, ex

        headers = {}
        api_key = temp_cfg.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if vendor in ("OpenAI", "DeepSeek", "智谱 ChatGLM"):
            url = f"{base}/v1/models" if base else ""
            ok, r = _probe(url or base or "https://api.openai.com", "GET", headers)
        elif vendor == "阿里通义":
            url = f"{base}/api/v1/services/aigc/text-generation/generation" if base else ""
            ok, r = _probe(url or base or "https://dashscope.aliyuncs.com", "OPTIONS", headers)
        elif vendor == "百度千帆":
            ok, r = _probe(base or "https://qianfan.baidu.com", "HEAD", headers)
        else:
            ok, r = _probe(base, "HEAD", headers)

        if ok:
            QMessageBox.information(self, "测试通过", f"{vendor} 可达，HTTP {getattr(r, 'status_code', 'n/a')}")
        else:
            QMessageBox.warning(self, "测试失败", f"{vendor} 不可达：{r}")
