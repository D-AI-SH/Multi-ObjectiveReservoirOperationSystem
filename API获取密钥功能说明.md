# API获取密钥功能说明

## 功能概述

在API配置界面新增了"获取密钥"按钮，用户点击后可以直接跳转到对应厂商的API购买和密钥获取页面，简化了用户获取API密钥的流程。

## 主要改进

### 1. 新增获取密钥按钮

在API配置对话框的厂商选择区域添加了"获取密钥"按钮：

```python
# 添加获取密钥按钮
self.btn_get_key = QPushButton("获取密钥")
self.btn_get_key.clicked.connect(self._on_get_key)
top_layout.addWidget(self.btn_get_key)
```

### 2. 厂商购买页面链接配置

定义了各厂商的API购买页面链接：

```python
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
```

### 3. 点击事件处理

实现了 `_on_get_key()` 方法来处理按钮点击：

```python
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
```

## 支持的厂商和链接

| 厂商 | 购买页面链接 | 说明 |
|------|-------------|------|
| OpenAI | https://platform.openai.com/api-keys | OpenAI官方API密钥管理页面 |
| 百度千帆 | https://console.bce.baidu.com/qianfan/overview | 百度智能云千帆大模型平台 |
| 阿里通义 | https://dashscope.console.aliyun.com/apiKey | 阿里云通义千问API密钥管理 |
| 讯飞星火 | https://console.xfyun.cn/services/spark | 科大讯飞星火认知大模型控制台 |
| 智谱 ChatGLM | https://open.bigmodel.cn/usercenter/apikeys | 智谱AI开放平台API密钥管理 |
| MiniMax | https://api.minimax.chat/console/app | MiniMax开发者控制台 |
| DeepSeek | https://platform.deepseek.com/api_keys | DeepSeek平台API密钥管理 |
| 硅基流动 | https://platform.ai-siliconflow.com/console | 硅基流动AI平台控制台 |
| 月之暗面 | https://platform.moonshot.cn/console/api-keys | 月之暗面平台API密钥管理 |

## 使用流程

### 1. 打开API配置界面
- 点击聊天助手界面的"API设置"按钮
- 或通过菜单打开API配置对话框

### 2. 选择厂商
- 从下拉框中选择需要获取API密钥的厂商

### 3. 获取密钥
- 点击"获取密钥"按钮
- 系统自动在默认浏览器中打开对应厂商的API购买页面
- 用户可以在网页中注册账号、购买服务、获取API密钥

### 4. 配置密钥
- 复制从网页获取的API密钥
- 粘贴到配置界面的对应字段
- 点击"保存"完成配置

## 技术实现细节

### 1. 浏览器打开机制

使用PyQt6的 `QDesktopServices.openUrl()` 方法：

```python
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

QDesktopServices.openUrl(QUrl(url))
```

### 2. 错误处理

- 检查厂商是否在支持列表中
- 捕获浏览器打开失败异常
- 提供友好的错误提示信息

### 3. 用户体验优化

- 点击后立即显示成功提示
- 自动使用系统默认浏览器
- 支持所有主流厂商的官方页面

## 功能优势

### 1. 简化用户操作
- 无需手动搜索厂商官网
- 一键直达API购买页面
- 减少配置过程中的困惑

### 2. 提高配置效率
- 直接跳转到正确的页面
- 避免访问错误的网站
- 节省查找时间

### 3. 增强用户体验
- 统一的获取密钥入口
- 清晰的视觉提示
- 友好的操作反馈

## 兼容性说明

- 支持Windows、macOS、Linux系统
- 使用系统默认浏览器打开链接
- 与现有API配置功能完全兼容

## 安全考虑

- 所有链接均为官方认证页面
- 不涉及用户敏感信息传输
- 仅提供页面跳转功能

## 总结

新增的"获取密钥"功能显著提升了API配置的用户体验：

- ✅ 一键跳转到官方购买页面
- ✅ 支持所有主流AI厂商
- ✅ 友好的错误处理和提示
- ✅ 与现有功能完美集成
- ✅ 跨平台兼容性保证

用户现在可以更便捷地获取和配置API密钥，大大简化了使用门槛。
