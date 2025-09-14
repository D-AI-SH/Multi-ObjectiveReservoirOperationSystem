import sys, pprint
pprint.pprint({'python': sys.executable, 'sys.path[0]': sys.path[0]})
import sys
from typing import Dict, Any
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QSplitter, QSplashScreen, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDialog, QLineEdit, QTextEdit, QCheckBox, QFormLayout, QDialogButtonBox, QMessageBox, QProgressBar

# 动态添加项目根目录到sys.path
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from dataLAYER.data_manager import DataManager
from uiLAYER.data_config_tab import DataConfigTab
from uiLAYER.data_management_tab import DataManagementTab
from uiLAYER.ui_utils import MODEL_DATA_REQUIREMENTS
from modelLAYER.model_manager import ModelManager
from uiLAYER.model_tab import ModelTab
from uiLAYER.schedule_tab import ScheduleTab
from visLAYER.vis_tab import VisTab
from scheduleLAYER.schedule_manager import ScheduleManager
from uiLAYER.chat_widget import ChatWidget
from compute_thread import ComputeThread
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor

class MainWindow(QMainWindow):
    """
    主窗口
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多目标水库调度系统")
        # 设置窗口图标
        self.setWindowIcon(QIcon("uiLAYER/assets/logo.png"))
        self.setGeometry(100, 100, 1200, 800)

        # 实例化管理器
        self.data_manager = DataManager(ai_enabled=False)  # 默认关闭AI功能
        self.model_manager = ModelManager()
        self.schedule_manager = ScheduleManager()
        
        # 创建计算线程
        self.compute_thread = ComputeThread(self)
        self._connect_compute_thread_signals()

        # 创建一个Tab窗口
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(True)

        # 创建各个层级的Tab  
        self.data_management_tab = DataManagementTab(self.data_manager)
        self.data_config_tab = DataConfigTab(self.data_manager)
        self.model_tab = ModelTab()
        self.schedule_tab = ScheduleTab()
        self.vis_tab = VisTab()
        
        # 连接所有信号和槽
        self.model_tab.model_selection_changed.connect(self.data_config_tab.update_ui_for_model)
        self.data_management_tab.data_pool_updated.connect(self.data_config_tab.refresh_data_sources)
        self.data_config_tab.link_changed.connect(self.data_management_tab.refresh_data_list)
        self.model_tab.run_button.clicked.connect(self.run_dispatch_model)
        self.schedule_tab.run_button.clicked.connect(self.run_schedule_optimization)

        tabs.addTab(self.data_management_tab, "数据管理")
        tabs.addTab(self.data_config_tab, "数据配置")
        tabs.addTab(self.model_tab, "模型配置")
        tabs.addTab(self.schedule_tab, "调度优化")
        tabs.addTab(self.vis_tab, "可视化结果")

        # 左侧容器：蓝色顶栏 + 标签页
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._header_color_default = "#E3F2FD"  # 浅蓝色背景
        self._header_color_running = "#FFF3E0"  # 浅橙色背景

        self.header_bar = QWidget()
        self.header_bar.setObjectName("HeaderBar")
        self.header_bar.setStyleSheet(
            f"#HeaderBar { { } }".replace("{ }", f"{{ background-color: {self._header_color_default}; }}")
            + "#HeaderBar QLabel#HeaderTitle { color: #333333; font-weight: 600; }"
            + "#HeaderBar QPushButton { background: transparent; color: #333333; border: 1px solid rgba(51,51,51,0.25);"
            + " border-radius: 4px; padding: 4px 10px; }"
            + "#HeaderBar QPushButton:hover { background: rgba(58,111,226,0.12); color: #3A6FE2; }"
            + "#HeaderBar QPushButton:pressed { background: rgba(58,111,226,0.2); color: #3A6FE2; }"
        )
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(8)
        self.btn_toggle_chat = QPushButton("隐藏聊天 ▶")
        self.btn_toggle_chat.setToolTip("向右折叠/展开聊天窗口")
        self.btn_toggle_chat.clicked.connect(self.toggle_chat_panel)
        header_layout.addWidget(self.btn_toggle_chat)
        header_layout.addStretch()
        
        # 添加导出按钮
        self.btn_export = QPushButton("导出结果")
        self.btn_export.setToolTip("导出模型结果和调度结果为CSV文件")
        self.btn_export.clicked.connect(self.export_results_to_csv)
        header_layout.addWidget(self.btn_export)
        
        # 添加取消计算按钮
        self.btn_cancel_compute = QPushButton("取消计算")
        self.btn_cancel_compute.setToolTip("取消当前正在运行的计算任务")
        self.btn_cancel_compute.clicked.connect(self.cancel_current_computation)
        self.btn_cancel_compute.setVisible(False)  # 默认隐藏
        header_layout.addWidget(self.btn_cancel_compute)
        
        header_layout.addStretch()
        self.header_title = QLabel("多目标水库调度系统")
        self.header_title.setObjectName("HeaderTitle")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()

        left_layout.addWidget(self.header_bar)
        left_layout.addWidget(tabs)

        # 右侧聊天窗口
        self.chat_widget = ChatWidget()
        # 隐藏聊天内部的折叠按钮，避免与顶栏重复
        if hasattr(self.chat_widget, "hide_internal_collapse_button"):
            self.chat_widget.hide_internal_collapse_button()
        
        # 启动时预加载向量检索器
        self._preload_vector_retriever()

        # 分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.chat_widget)
        self.splitter.setSizes([900, 300])

        self.setCentralWidget(self.splitter)

        # 折叠状态记录
        self._chat_collapsed = False
        self._splitter_prev_sizes = self.splitter.sizes()
        
        # 计算状态管理
        self._current_task_type = None  # 'model' 或 'schedule'
        self._progress_timer = QTimer()
        self._progress_timer.timeout.connect(self._update_progress_display)

    def _connect_compute_thread_signals(self):
        """连接计算线程信号"""
        self.compute_thread.progress_updated.connect(self._on_compute_progress_updated)
        self.compute_thread.model_completed.connect(self._on_model_completed)
        self.compute_thread.schedule_completed.connect(self._on_schedule_completed)
        self.compute_thread.error_occurred.connect(self._on_compute_error)
        self.compute_thread.task_finished.connect(self._on_task_finished)
    
    def _preload_vector_retriever(self):
        """预加载向量检索器，避免首次使用时延迟"""
        try:
            # 在后台线程中预加载向量检索器
            from PyQt6.QtCore import QThread, QObject, pyqtSignal
            
            class PreloadWorker(QObject):
                finished = pyqtSignal()
                
                def __init__(self, chat_widget):
                    super().__init__()
                    self.chat_widget = chat_widget
                
                def run(self):
                    try:
                        # 调用聊天组件的向量检索器预加载方法
                        if hasattr(self.chat_widget, '_ensure_retriever'):
                            self.chat_widget._ensure_retriever()
                        self.finished.emit()
                    except Exception as e:
                        print(f"预加载向量检索器失败: {e}")
                        self.finished.emit()
            
            # 创建后台线程
            self.preload_thread = QThread()
            self.preload_worker = PreloadWorker(self.chat_widget)
            self.preload_worker.moveToThread(self.preload_thread)
            
            # 连接信号
            self.preload_thread.started.connect(self.preload_worker.run)
            self.preload_worker.finished.connect(self.preload_thread.quit)
            self.preload_worker.finished.connect(self.preload_worker.deleteLater)
            self.preload_thread.finished.connect(self.preload_thread.deleteLater)
            
            # 启动线程
            self.preload_thread.start()
            
            print("向量检索器预加载已启动...")
            
        except Exception as e:
            print(f"预加载向量检索器时出错: {e}")

    def toggle_chat_panel(self):
        """在分割器中向右折叠/展开聊天窗格。"""
        try:
            sizes = self.splitter.sizes()
            if not self._chat_collapsed:
                # 记录当前尺寸并将右侧聊天折叠为 0
                self._splitter_prev_sizes = sizes
                total = sum(sizes) or max(self.width(), 1200)
                left_size = max(total - 1, 1)
                self.splitter.setSizes([left_size, 0])
                self._chat_collapsed = True
                if hasattr(self, 'btn_toggle_chat'):
                    self.btn_toggle_chat.setText("显示聊天 ◀")
            else:
                prev = getattr(self, '_splitter_prev_sizes', [])
                if not prev or (len(prev) >= 2 and prev[1] == 0):
                    # 兜底：按照 3:1 恢复比例
                    total = self.splitter.width() or sum(sizes) or 1200
                    left = int(total * 0.75)
                    right = max(total - left, 240)
                    self.splitter.setSizes([left, right])
                else:
                    self.splitter.setSizes(prev)
                self._chat_collapsed = False
                if hasattr(self, 'btn_toggle_chat'):
                    self.btn_toggle_chat.setText("隐藏聊天 ▶")
        except Exception:
            # 出现异常时尽可能不影响主线程
            pass

    # ---------------- 顶栏状态切换：运行态/空闲态 ----------------
    def _apply_header_style(self, bg_color: str) -> None:
        self.header_bar.setStyleSheet(
            f"#HeaderBar {{ background-color: {bg_color}; }}"
            + "#HeaderBar QLabel#HeaderTitle { color: #333333; font-weight: 600; }"
            + "#HeaderBar QPushButton { background: transparent; color: #333333; border: 1px solid rgba(51,51,51,0.25);"
            + " border-radius: 4px; padding: 4px 10px; }"
            + "#HeaderBar QPushButton:hover { background: rgba(58,111,226,0.12); color: #3A6FE2; }"
            + "#HeaderBar QPushButton:pressed { background: rgba(58,111,226,0.2); color: #3A6FE2; }"
        )

    def _set_header_running(self, running: bool) -> None:
        if running:
            self.header_title.setText("正在运行计算")
            self._apply_header_style(self._header_color_running)
            self.btn_cancel_compute.setVisible(True)
        else:
            self.header_title.setText("多目标水库调度系统")
            self._apply_header_style(self._header_color_default)
            self.btn_cancel_compute.setVisible(False)
        QApplication.processEvents()

    def run_dispatch_model(self):
        """
        根据数据链接运行调度模型，并可视化结果。
        支持多水库运行。
        """
        # 检查计算线程是否忙碌
        if self.compute_thread.is_busy():
            print("警告：计算线程正在运行中，请等待当前任务完成")
            return
            
        selected_model = self.model_tab.model_combo.currentText()
        if not selected_model or selected_model not in MODEL_DATA_REQUIREMENTS:
            print("错误：请先选择一个有效的模型。")
            return
            
        required_ids = MODEL_DATA_REQUIREMENTS[selected_model]
        
        # 获取水库数量
        reservoir_count = self.data_config_tab.reservoir_count
        
        # 获取多水库输入数据
        reservoir_input_data = self.data_manager.get_multi_reservoir_input_data(required_ids, reservoir_count)
        
        if not reservoir_input_data:
            print("错误：未能成功准备多水库输入数据，请检查数据配置。")
            return

        # 从动态UI获取参数
        params = self.model_tab.get_params()
        if any(p is None for p in params.values()):
            print("错误：一个或多个模型参数无效，请检查输入。")
            return
        
        # 设置当前任务类型
        self._current_task_type = 'model'
        
        # 启动计算线程
        self._set_header_running(True)
        self._progress_timer.start(100)  # 每100ms更新一次进度显示
        
        success = self.compute_thread.run_model_computation(
            selected_model, reservoir_input_data, params, required_ids
        )
        
        if not success:
            self._set_header_running(False)
            self._progress_timer.stop()
            print("错误：无法启动模型计算线程")

    def run_schedule_optimization(self):
        """
        根据用户在调度优化标签页的设置运行多目标调度算法。
        """
        # 检查计算线程是否忙碌
        if self.compute_thread.is_busy():
            print("警告：计算线程正在运行中，请等待当前任务完成")
            return
            
        objectives = self.schedule_tab.get_objectives()
        params = self.schedule_tab.get_all_params()  # 获取所有参数，包括水库物理参数

        # 从 data_manager 获取多水库数据作为调度优化输入
        multi_reservoir_results = self.data_manager.get_multi_reservoir_results()
        
        # 使用模型结果作为调度优化的输入
        input_data = multi_reservoir_results.get('model_results', {})
        if not input_data:
            print("警告：未找到模型结果数据，使用空数据运行调度优化")
            input_data = None

        # 传递完整的多水库数据给调度管理器
        schedule_input = {
            'model_results': input_data,
            'reservoir_count': len(input_data) if input_data else 1
        }

        # 设置当前任务类型
        self._current_task_type = 'schedule'
        
        # 启动计算线程
        self._set_header_running(True)
        self._progress_timer.start(100)  # 每100ms更新一次进度显示
        
        success = self.compute_thread.run_schedule_optimization(objectives, params, schedule_input)
        
        if not success:
            self._set_header_running(False)
            self._progress_timer.stop()
            print("错误：无法启动调度优化计算线程")

    def _print_schedule_strategy(self, strategy_report: Dict[str, Any]):
        """打印调度策略信息"""
        if not strategy_report:
            print("未找到调度策略信息")
            return
        
        print("\n" + "="*60)
        print("调度策略报告")
        print("="*60)
        
        # 打印摘要信息
        summary = strategy_report.get('summary', {})
        print(f"水库数量: {summary.get('total_reservoirs', 0)}")
        print(f"优化目标: {', '.join(summary.get('active_objectives', []))}")
        print(f"帕累托解总数: {summary.get('total_pareto_solutions', 0)}")
        
        # 打印每个水库的策略
        reservoir_strategies = strategy_report.get('reservoir_strategies', [])
        for strategy in reservoir_strategies:
            res_id = strategy.get('reservoir_id', 0)
            print(f"\n水库 {res_id} 调度策略:")
            print(f"  帕累托解数量: {strategy.get('pareto_solutions_count', 0)}")
            
            # 打印推荐策略
            recommendations = strategy.get('recommended_strategies', [])
            for rec in recommendations:
                print(f"  {rec.get('description', '')}")
                print(f"    解ID: {rec.get('solution_id', 0)}")
                obj_values = rec.get('objective_values', [])
                if obj_values:
                    print(f"    目标值: {obj_values}")
        
        # 打印实施指导
        implementation = strategy_report.get('implementation_guidance', {})
        if implementation:
            print(f"\n实施指导:")
            for res_id, recs in enumerate(implementation.get('operational_recommendations', []), 1):
                print(f"  水库 {res_id} 操作建议:")
                for rec in recs.get('recommendations', []):
                    print(f"    - {rec}")
        
        print("="*60)

    # ================ 计算线程信号处理方法 ================
    
    def _on_compute_progress_updated(self, progress: int, message: str):
        """处理计算进度更新"""
        # 更新标题栏显示进度
        if self._current_task_type == 'model':
            self.header_title.setText(f"正在运行模型计算... {progress}%")
        elif self._current_task_type == 'schedule':
            self.header_title.setText(f"正在运行调度优化... {progress}%")
        
        print(f"计算进度: {progress}% - {message}")
        QApplication.processEvents()
    
    def _on_model_completed(self, reservoir_results: dict, failures: dict):
        """处理模型计算完成"""
        try:
            if reservoir_results:
                # 存储结果到数据管理器
                self.data_manager.store_multi_reservoir_results({'model_results': reservoir_results})
                
                # 获取输入数据用于可视化
                selected_model = self.model_tab.model_combo.currentText()
                required_ids = MODEL_DATA_REQUIREMENTS[selected_model]
                reservoir_count = self.data_config_tab.reservoir_count
                reservoir_input_data = self.data_manager.get_multi_reservoir_input_data(required_ids, reservoir_count)
                
                # 更新可视化界面
                self.vis_tab.set_input_data(reservoir_input_data)
                self.vis_tab.set_model_results(reservoir_results)
                print(f"多水库模型运行完成，共 {len(reservoir_results)} 个水库")
            else:
                print("错误：所有水库模型运行均失败")

            # 获取参数用于报告
            params = self.model_tab.get_params()
            selected_model = self.model_tab.model_combo.currentText()
            
            # 在 AI 助手界面生成报告
            self.chat_widget.show_model_run_report(selected_model, reservoir_results, params, failures=failures)
            
        except Exception as e:
            print(f"处理模型计算结果时出错: {e}")
    
    def _on_schedule_completed(self, schedule_results: dict):
        """处理调度优化完成"""
        try:
            # 输出调度策略信息
            schedule_strategy = schedule_results.get('schedule_strategy', {})
            self._print_schedule_strategy(schedule_strategy)
            
            # 更新可视化界面
            self.vis_tab.set_schedule_results(schedule_results)
            
            # 自动选择调度优化结果数据类型并显示
            self.vis_tab.data_type_combo.setCurrentText("调度优化结果")
            self.vis_tab.on_data_type_changed()
            
            # 存储调度优化结果到数据管理器
            self.data_manager.store_multi_reservoir_results({'schedule_results': schedule_results})
            
            # 获取参数用于报告
            objectives = self.schedule_tab.get_objectives()
            params = self.schedule_tab.get_all_params()
            
            # 生成并显示调度优化报告
            self.chat_widget.show_schedule_optimization_report(objectives, params, schedule_results)
            
        except Exception as e:
            print(f"处理调度优化结果时出错: {e}")
    
    def _on_compute_error(self, error_type: str, error_message: str):
        """处理计算错误"""
        print(f"计算错误 ({error_type}): {error_message}")
        
        # 显示错误消息框
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            self, 
            "计算错误", 
            f"计算过程中发生错误:\n\n类型: {error_type}\n消息: {error_message}"
        )
    
    def _on_task_finished(self):
        """处理任务完成"""
        self._set_header_running(False)
        self._progress_timer.stop()
        self._current_task_type = None
        print("计算任务完成")
    
    def _update_progress_display(self):
        """更新进度显示（定时器回调）"""
        # 这里可以添加更详细的进度显示逻辑
        # 目前主要依赖信号回调来更新进度
        pass
    
    def cancel_current_computation(self):
        """取消当前计算任务"""
        if self.compute_thread.is_busy():
            reply = QMessageBox.question(
                self,
                "确认取消",
                "确定要取消当前正在运行的计算任务吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.compute_thread.cancel_current_task()
                print("用户取消了计算任务")
                # 注意：实际的取消逻辑在计算线程中处理
        else:
            print("当前没有正在运行的计算任务")

    def export_results_to_csv(self):
        """
        导出模型结果和调度结果为CSV文件
        允许用户选择保存路径，每个水库模型结果一个文件，调度结果一个文件
        """
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QProgressBar
            import pandas as pd
            import os
            from datetime import datetime
            
            # 获取当前结果数据
            multi_reservoir_results = self.data_manager.get_multi_reservoir_results()
            
            if not multi_reservoir_results:
                QMessageBox.information(self, "提示", "暂无结果数据可导出")
                return
            
            # 创建导出配置对话框
            export_dialog = ExportConfigDialog(multi_reservoir_results, self)
            if export_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            # 获取用户选择的导出选项
            export_options = export_dialog.get_export_options()
            
            # 让用户选择保存目录
            save_dir = QFileDialog.getExistingDirectory(
                self, 
                "选择保存目录", 
                os.path.expanduser("~/Desktop"),
                QFileDialog.Option.ShowDirsOnly
            )
            
            if not save_dir:
                return
            
            # 创建进度对话框
            progress_dialog = ExportProgressDialog(self)
            progress_dialog.show()
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            exported_files = []
            total_files = 0
            current_file = 0
            
            try:
                # 计算总文件数
                if export_options['export_model_results']:
                    model_results = multi_reservoir_results.get('model_results', {})
                    total_files += len([r for r in model_results.values() if r is not None and not r.empty])
                
                if export_options['export_schedule_results']:
                    schedule_results = multi_reservoir_results.get('schedule_results', {})
                    if schedule_results.get('optimization_results') is not None:
                        total_files += 1
                    if schedule_results.get('objectives') is not None:
                        total_files += 1
                    if schedule_results.get('pareto_front') is not None:
                        total_files += 1
                
                progress_dialog.setMaximum(total_files)
                
                # 导出模型结果（每个水库一个文件）
                if export_options['export_model_results']:
                    model_results = multi_reservoir_results.get('model_results', {})
                    if model_results:
                        for reservoir_id, results_df in model_results.items():
                            if results_df is not None and not results_df.empty:
                                filename = f"水库{reservoir_id}_模型结果_{timestamp}.csv"
                                filepath = os.path.join(save_dir, filename)
                                
                                try:
                                    progress_dialog.setLabelText(f"正在导出: {filename}")
                                    results_df.to_csv(filepath, index=True, encoding='utf-8-sig')
                                    exported_files.append(filename)
                                    current_file += 1
                                    progress_dialog.setValue(current_file)
                                    print(f"已导出水库 {reservoir_id} 模型结果: {filepath}")
                                except Exception as e:
                                    print(f"导出水库 {reservoir_id} 模型结果失败: {e}")
                
                # 导出调度优化结果
                if export_options['export_schedule_results']:
                    schedule_results = multi_reservoir_results.get('schedule_results', {})
                    if schedule_results:
                        # 导出优化结果
                        optimization_results = schedule_results.get('optimization_results')
                        if optimization_results is not None and not optimization_results.empty:
                            filename = f"调度优化结果_{timestamp}.csv"
                            filepath = os.path.join(save_dir, filename)
                            
                            try:
                                progress_dialog.setLabelText(f"正在导出: {filename}")
                                optimization_results.to_csv(filepath, index=True, encoding='utf-8-sig')
                                exported_files.append(filename)
                                current_file += 1
                                progress_dialog.setValue(current_file)
                                print(f"已导出调度优化结果: {filepath}")
                            except Exception as e:
                                print(f"导出调度优化结果失败: {e}")
                        
                        # 导出目标函数结果
                        objectives = schedule_results.get('objectives')
                        if objectives is not None and not objectives.empty:
                            filename = f"目标函数结果_{timestamp}.csv"
                            filepath = os.path.join(save_dir, filename)
                            
                            try:
                                progress_dialog.setLabelText(f"正在导出: {filename}")
                                objectives.to_csv(filepath, index=True, encoding='utf-8-sig')
                                exported_files.append(filename)
                                current_file += 1
                                progress_dialog.setValue(current_file)
                                print(f"已导出目标函数结果: {filepath}")
                            except Exception as e:
                                print(f"导出目标函数结果失败: {e}")
                        
                        # 导出帕累托前沿数据
                        pareto_front = schedule_results.get('pareto_front')
                        if pareto_front is not None and not pareto_front.empty:
                            filename = f"帕累托前沿_{timestamp}.csv"
                            filepath = os.path.join(save_dir, filename)
                            
                            try:
                                progress_dialog.setLabelText(f"正在导出: {filename}")
                                pareto_front.to_csv(filepath, index=True, encoding='utf-8-sig')
                                exported_files.append(filename)
                                current_file += 1
                                progress_dialog.setValue(current_file)
                                print(f"已导出帕累托前沿数据: {filepath}")
                            except Exception as e:
                                print(f"导出帕累托前沿数据失败: {e}")
                
                progress_dialog.close()
                
                # 显示导出结果
                if exported_files:
                    message = f"成功导出 {len(exported_files)} 个文件到:\n{save_dir}\n\n导出的文件:\n" + "\n".join(exported_files)
                    QMessageBox.information(self, "导出成功", message)
                    
                    # 询问是否打开保存目录
                    reply = QMessageBox.question(
                        self, 
                        "打开文件夹", 
                        "是否打开保存目录？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        try:
                            import subprocess
                            import platform
                            
                            if platform.system() == "Windows":
                                os.startfile(save_dir)
                            elif platform.system() == "Darwin":  # macOS
                                subprocess.run(["open", save_dir])
                            else:  # Linux
                                subprocess.run(["xdg-open", save_dir])
                        except Exception as e:
                            print(f"打开文件夹失败: {e}")
                else:
                    QMessageBox.warning(self, "导出失败", "没有找到可导出的结果数据")
                    
            finally:
                progress_dialog.close()
                
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出过程中发生错误:\n{str(e)}")
            print(f"导出结果时出错: {e}")


class ExportConfigDialog(QDialog):
    """导出配置对话框"""
    
    def __init__(self, results_data, parent=None):
        super().__init__(parent)
        self.results_data = results_data
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("导出配置")
        self.setModal(True)
        self.resize(400, 300)
        
        # 设置浅色主题样式
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #333333;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
            }
            QCheckBox {
                color: #333333;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #CCCCCC;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3A6FE2;
                background-color: #3A6FE2;
            }
            QPushButton {
                background-color: #F5F5F5;
                color: #333333;
                border: 1px solid #CCCCCC;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3A6FE2;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #1E3F88;
                color: #FFFFFF;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择要导出的数据类型:")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px; color: #333333;")
        layout.addWidget(title_label)
        
        # 导出选项
        self.export_model_checkbox = QCheckBox("模型结果")
        self.export_model_checkbox.setChecked(True)
        if not self.results_data.get('model_results'):
            self.export_model_checkbox.setEnabled(False)
            self.export_model_checkbox.setToolTip("暂无模型结果数据")
        layout.addWidget(self.export_model_checkbox)
        
        self.export_schedule_checkbox = QCheckBox("调度优化结果")
        self.export_schedule_checkbox.setChecked(True)
        if not self.results_data.get('schedule_results'):
            self.export_schedule_checkbox.setEnabled(False)
            self.export_schedule_checkbox.setToolTip("暂无调度优化结果数据")
        layout.addWidget(self.export_schedule_checkbox)
        
        # 数据预览
        preview_label = QLabel("可导出的数据:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 20px; color: #333333;")
        layout.addWidget(preview_label)
        
        preview_text = QLabel()
        preview_lines = []
        
        model_results = self.results_data.get('model_results', {})
        if model_results:
            preview_lines.append(f"• 模型结果: {len(model_results)} 个水库")
        
        schedule_results = self.results_data.get('schedule_results', {})
        if schedule_results:
            preview_lines.append("• 调度优化结果:")
            if schedule_results.get('optimization_results') is not None:
                preview_lines.append("  - 优化结果数据")
            if schedule_results.get('objectives') is not None:
                preview_lines.append("  - 目标函数结果")
            if schedule_results.get('pareto_front') is not None:
                preview_lines.append("  - 帕累托前沿数据")
        
        if not preview_lines:
            preview_lines.append("暂无数据")
        
        preview_text.setText("\n".join(preview_lines))
        preview_text.setStyleSheet("background-color: #F8F9FA; color: #333333; padding: 10px; border: 1px solid #DEE2E6; border-radius: 4px;")
        layout.addWidget(preview_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self.accept)
        export_btn.setDefault(True)
        button_layout.addWidget(export_btn)
        
        layout.addLayout(button_layout)
    
    def get_export_options(self):
        """获取导出选项"""
        return {
            'export_model_results': self.export_model_checkbox.isChecked(),
            'export_schedule_results': self.export_schedule_checkbox.isChecked()
        }


class ExportProgressDialog(QDialog):
    """导出进度对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("导出进度")
        self.setModal(True)
        self.resize(400, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        # 设置浅色主题样式
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #333333;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
            }
            QProgressBar {
                border: 2px solid #DEE2E6;
                border-radius: 5px;
                text-align: center;
                background-color: #F8F9FA;
            }
            QProgressBar::chunk {
                background-color: #3A6FE2;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 进度标签
        self.label = QLabel("正在准备导出...")
        layout.addWidget(self.label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
    
    def setLabelText(self, text):
        """设置标签文本"""
        self.label.setText(text)
        QApplication.processEvents()
    
    def setValue(self, value):
        """设置进度值"""
        self.progress_bar.setValue(value)
        QApplication.processEvents()
    
    def setMaximum(self, maximum):
        """设置最大值"""
        self.progress_bar.setMaximum(maximum)
        if maximum > 0:
            self.status_label.setText(f"0 / {maximum}")
    
    def setStatusText(self, text):
        """设置状态文本"""
        self.status_label.setText(text)
        QApplication.processEvents()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 使用更现代、跨平台的 Fusion 样式基础
    app.setStyle("Fusion")

    # 应用自定义深色主题样式表
    from uiLAYER.theme import STYLE as APP_STYLE
    app.setStyleSheet(APP_STYLE)

    # ---- 启动画面 ----
    logo_path = "uiLAYER/assets/logo.png"
    pixmap = QPixmap(logo_path)
    if pixmap.isNull():
        # 如果找不到 logo，则创建一个临时的纯色 pixmap
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor("#FFFFFF"))

    splash = QSplashScreen(pixmap)
    splash.showMessage("系统启动中...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.black)
    splash.show()
    app.processEvents()

    window = MainWindow()
    window.show()

    splash.finish(window)
    sys.exit(app.exec())
