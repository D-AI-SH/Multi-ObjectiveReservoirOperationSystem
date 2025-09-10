# 多目标水库调度系统

## 项目简介

这是一个基于 PyQt6 开发的多目标水库调度系统，集成了数据管理、模型计算、调度优化和可视化分析等功能。系统采用分层架构设计，具有良好的可扩展性和维护性。

## 系统架构

```
多目标水库调度系统/
├── mainLAYER/          # 主程序层
├── uiLAYER/            # 用户界面层
├── dataLAYER/          # 数据管理层
├── modelLAYER/         # 模型计算层
├── scheduleLAYER/      # 调度优化层
├── visLAYER/           # 可视化层
├── data/               # 数据文件
├── config/             # 配置文件
│   ├── api_keys.json           # API密钥配置
│   └── data_links_config.json  # 数据链接配置
└── 打包工具/           # 软件打包相关脚本
```

## 核心功能模块

### 🖥️ 主程序层 (mainLAYER)
- **main.py** - 系统主入口，负责启动应用程序和初始化主窗口

### 🎨 用户界面层 (uiLAYER)
- **main_window.py** - 主窗口界面，包含所有功能选项卡
- **data_config_tab.py** - 数据配置选项卡，用于配置数据源和列映射
- **date_range_selector.py** - 日期范围选择器，支持多数据源日期对齐
- **theme.py** - 界面主题和样式配置
- **assets/** - 界面资源文件（图标、图片等）

### 📊 数据管理层 (dataLAYER)
- **data_manager.py** - 数据管理器，负责数据的读取、处理和存储
- **database_manager.py** - 数据库管理器，处理数据库连接和操作
- **data_processor.py** - 数据处理器，进行数据清洗和预处理

### 🧮 模型计算层 (modelLAYER)
- **model_base.py** - 模型基类，定义模型接口
- **optimization_model.py** - 优化模型实现
- **evaluation_model.py** - 评估模型实现

### ⚡ 调度优化层 (scheduleLAYER)
- **scheduler.py** - 调度器，实现水库调度算法
- **constraint_handler.py** - 约束处理器，处理各种约束条件

### 📈 可视化层 (visLAYER)
- **chart_manager.py** - 图表管理器，负责各种图表的生成和显示
- **plot_utils.py** - 绘图工具函数

### ⚙️ 配置管理层 (config/)
- **config_manager.py** - 配置管理器，统一管理所有配置文件的访问和操作
- **api_keys.json** - API密钥配置文件，存储各种服务的访问密钥
- **data_links_config.json** - 数据链接配置文件，管理水库与数据源的关联关系
