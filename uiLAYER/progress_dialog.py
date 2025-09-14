#!/usr/bin/env python3
"""
进度对话框模块
提供导入数据时的进度显示功能
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QProgressBar, QLabel, QPushButton)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class ProgressDialog(QDialog):
    """进度对话框，用于显示长时间操作的进度"""
    
    # 信号定义
    canceled = pyqtSignal()
    
    def __init__(self, parent=None, title="处理中", message="正在处理，请稍候..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border: 1px solid #DEE2E6;
            }
            QLabel {
                color: #374151;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #DEE2E6;
                border-radius: 3px;
                text-align: center;
                background-color: #F8F9FA;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #DEE2E6;
                border-radius: 3px;
                padding: 5px 15px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        self._setup_ui(message)
        self._setup_timer()
        
    def _setup_ui(self, message):
        """设置用户界面"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 消息标签
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(10)
        self.message_label.setFont(font)
        layout.addWidget(self.message_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        self.progress_bar.setMinimumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # 详细状态标签
        self.status_label = QLabel("准备中...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #6B7280; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def _setup_timer(self):
        """设置定时器用于更新进度条动画"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(100)  # 每100ms更新一次
        
    def _update_progress(self):
        """更新进度条动画"""
        current = self.progress_bar.value()
        if current >= 100:
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setValue(current + 2)
            
    def _on_cancel(self):
        """取消按钮点击事件"""
        self.canceled.emit()
        self.close()
        
    def set_message(self, message):
        """设置消息文本"""
        self.message_label.setText(message)
        
    def set_status(self, status):
        """设置状态文本"""
        self.status_label.setText(status)
        
    def set_determinate_progress(self, value, maximum=100):
        """设置为确定模式并设置进度值"""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
        
    def set_indeterminate_progress(self):
        """设置为不确定模式"""
        self.progress_bar.setRange(0, 0)
        
    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        super().closeEvent(event)


class ImportProgressDialog(ProgressDialog):
    """专门用于导入数据的进度对话框"""
    
    def __init__(self, parent=None, total_files=1):
        super().__init__(parent, "导入数据", "正在导入数据文件...")
        self.total_files = total_files
        self.current_file = 0
        self.current_file_name = ""
        
    def set_file_progress(self, file_index, file_name, status=""):
        """设置文件导入进度"""
        self.current_file = file_index
        self.current_file_name = file_name
        
        # 计算总体进度
        if self.total_files > 0:
            progress = int((file_index / self.total_files) * 100)
            self.set_determinate_progress(progress)
        
        # 更新消息
        message = f"正在导入文件 ({file_index + 1}/{self.total_files}):\n{file_name}"
        self.set_message(message)
        
        if status:
            self.set_status(status)
        else:
            self.set_status("读取文件数据...")
            
    def set_processing_status(self, status):
        """设置处理状态"""
        self.set_status(status)
        
    def set_import_complete(self, success_count, total_count):
        """设置导入完成状态"""
        self.set_determinate_progress(100)
        if success_count == total_count:
            self.set_message(f"导入完成！成功导入 {success_count} 个文件。")
            self.set_status("所有文件导入成功")
        else:
            self.set_message(f"导入完成！成功导入 {success_count}/{total_count} 个文件。")
            self.set_status(f"有 {total_count - success_count} 个文件导入失败")
        
        # 更改取消按钮为确定按钮
        self.cancel_button.setText("确定")
        try:
            self.cancel_button.clicked.disconnect()
        except:
            pass  # 如果没有连接，会抛出异常，忽略即可
        self.cancel_button.clicked.connect(self.close)
