#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI配置对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QPushButton, QGroupBox, QTextEdit,
    QLineEdit, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class AIConfigDialog(QDialog):
    """AI配置对话框"""
    
    config_changed = pyqtSignal(dict)  # 配置改变信号
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.current_config = current_config or {}
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI智能列名整理配置")
        self.setFixedSize(500, 450)
        
        layout = QVBoxLayout()
        
        # AI功能开关
        ai_group = QGroupBox("AI智能列名整理")
        ai_layout = QVBoxLayout()
        
        self.ai_enabled_cb = QCheckBox("启用AI智能列名翻译")
        self.ai_enabled_cb.setChecked(self.current_config.get('ai_enabled', False))
        self.ai_enabled_cb.toggled.connect(self.on_ai_toggled)
        ai_layout.addWidget(self.ai_enabled_cb)
        
        # AI API配置
        api_group = QGroupBox("AI智能助手API配置")
        api_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setText(self.current_config.get('api_key', ''))
        api_layout.addRow("API密钥:", self.api_key_edit)
        
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setText(self.current_config.get('api_url', 'https://api.ai-assistant.com/v1/chat/completions'))
        api_layout.addRow("API地址:", self.api_url_edit)
        
        self.model_edit = QLineEdit()
        self.model_edit.setText(self.current_config.get('model', 'gpt-3.5-turbo'))
        api_layout.addRow("模型:", self.model_edit)
        
        api_group.setLayout(api_layout)
        ai_layout.addWidget(api_group)
        
        # 功能说明
        info_text = QTextEdit()
        info_text.setMaximumHeight(120)
        info_text.setReadOnly(True)
        info_text.setPlainText("""
AI智能列名整理功能说明：
• 自动识别和翻译英文列名为中文
• 专门针对水文、气象、发电等相关术语进行智能匹配
• 支持时间相关术语的翻译
• 仅用于列名整理，不会处理其他数据内容
• 需要配置有效的AI智能助手API密钥才能使用

支持的术语类型：
• 水文：flow(流量)、level(水位)、storage(库容)等
• 气象：temperature(温度)、precipitation(降水量)等  
• 发电：power(发电量)、generation(发电功率)等
• 时间：year(年份)、month(月份)、hour(小时)等
        """.strip())
        ai_layout.addWidget(info_text)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 初始状态
        self.on_ai_toggled(self.ai_enabled_cb.isChecked())
    
    def on_ai_toggled(self, enabled):
        """AI开关状态改变"""
        self.api_key_edit.setEnabled(enabled)
        self.api_url_edit.setEnabled(enabled)
        self.model_edit.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)
    
    def test_connection(self):
        """测试AI API连接"""
        if not self.ai_enabled_cb.isChecked():
            QMessageBox.warning(self, "警告", "请先启用AI功能")
            return
        
        api_key = self.api_key_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        model = self.model_edit.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "警告", "请输入API密钥")
            return
        
        if not api_url:
            QMessageBox.warning(self, "警告", "请输入API地址")
            return
        
        try:
            import requests
            import json
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "请将以下英文列名翻译为中文：flow"}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    translation = result['choices'][0]['message']['content'].strip()
                    QMessageBox.information(self, "连接成功", 
                                          f"API连接测试成功！\n\n测试翻译结果：\nflow → {translation}")
                else:
                    QMessageBox.warning(self, "连接失败", 
                                      f"API返回格式异常：\n{result}")
            else:
                QMessageBox.warning(self, "连接失败", 
                                  f"HTTP状态码：{response.status_code}\n响应内容：{response.text}")
                
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "连接失败", f"网络请求失败：\n{str(e)}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "连接失败", f"响应解析失败：\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "连接失败", f"未知错误：\n{str(e)}")
    
    def get_config(self):
        """获取配置"""
        return {
            'ai_enabled': self.ai_enabled_cb.isChecked(),
            'api_key': self.api_key_edit.text().strip(),
            'api_url': self.api_url_edit.text().strip(),
            'model': self.model_edit.text().strip()
        }
    
    def accept(self):
        """确认配置"""
        config = self.get_config()
        
        if config['ai_enabled']:
            if not config['api_key']:
                QMessageBox.warning(self, "警告", "启用AI功能需要配置API密钥")
                return
        
        self.config_changed.emit(config)
        super().accept()
