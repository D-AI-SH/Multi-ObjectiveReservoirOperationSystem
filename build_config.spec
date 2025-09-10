# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(os.getcwd()).absolute()

# 数据文件收集
datas = [
    # 数据文件
    (str(project_root / 'data'), 'data'),
    # 配置文件（不包含API密钥）
    (str(project_root / 'config' / 'data_links_config.json'), 'config'),
    (str(project_root / 'config' / 'saint_venant_config.json'), 'config'),
    (str(project_root / 'config' / 'ai_performance_config_commented.json'), 'config'),
    # UI资源文件
    (str(project_root / 'uiLAYER' / 'assets'), 'uiLAYER/assets'),
    # 示例数据
    (str(project_root / 'example_data'), 'example_data'),
    (str(project_root / 'examples'), 'examples'),
    # 文档文件
    (str(project_root / 'docs'), 'docs'),
    (str(project_root / 'README.md'), '.'),
    (str(project_root / '使用手册.md'), '.'),
    (str(project_root / '增强日期选择器使用指南.md'), '.'),
]

# 隐藏导入（PyInstaller可能无法自动检测的模块）
hiddenimports = [
    # PyQt6相关
    'PyQt6.QtCore',
    'PyQt6.QtWidgets', 
    'PyQt6.QtGui',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineCore',
    'PyQt6.sip',
    
    # 科学计算
    'numpy',
    'pandas',
    'scipy',
    'sklearn',
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    'matplotlib.backends.backend_agg',
    'seaborn',
    'plotly',
    'plotly.graph_objects',
    'plotly.express',
    
    # 机器学习
    'sentence_transformers',
    'transformers',
    'torch',
    'faiss',
    
    # 优化算法
    'pymoo',
    'pymoo.core',
    'pymoo.algorithms',
    'pymoo.operators',
    'pymoo.problems',
    'pymoo.termination',
    'pymoo.optimize',
    
    # Web相关
    'flask',
    'dash',
    'dash.dependencies',
    'dash.html',
    'dash.dcc',
    'requests',
    'aiohttp',
    'websockets',
    
    # 数据处理
    'openpyxl',
    'xlrd',
    'lxml',
    'beautifulsoup4',
    'html5lib',
    'markdown',
    'markdownify',
    
    # 其他
    'sqlite3',
    'pickle',
    'json',
    'pathlib',
    'typing',
    'datetime',
    'threading',
    'multiprocessing',
]

# 排除的模块（减少打包体积）
excludes = [
    'tkinter',
    'unittest',
    'test',
    'tests',
    'pytest',
    'jupyter',
    'notebook',
    'IPython',
    # 排除PyQt5以避免与PyQt6冲突
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtWebEngineCore',
    'PyQt5.sip',
]

# 二进制文件
binaries = []

# 分析主程序
a = Analysis(
    ['mainLAYER/main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 创建PYZ文件
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='多目标水库调度系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='uiLAYER/assets/bot.ico',  # 设置图标
    version='version_info.txt'  # 版本信息文件
)
