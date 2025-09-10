# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent

# 数据文件列表
datas = [
    ("data/manual_faiss.index", "data"),
    ("data/manual_meta.pkl", "data"),
    ("data/project_database.db", "data"),
    ("data/examples", "data/examples"),
    ("data/reservoirs", "data/reservoirs"),
    ("config/data_links_config.json", "config"),
    ("config/saint_venant_config.json", "config"),
    ("config/ai_performance_config_commented.json", "config"),
    ("uiLAYER/assets", "uiLAYER/assets"),
    ("docs", "docs"),
]

# 隐藏导入
hiddenimports = [
    "PyQt6.QtCore",
    "PyQt6.QtWidgets",
    "PyQt6.QtGui",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "pandas",
    "numpy",
    "matplotlib",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_agg",
    "openpyxl",
    "xlrd",
    "sklearn",
    "scipy",
    "pymoo",
    "faiss",
    "sentence_transformers",
    "transformers",
    "torch",
    "plotly",
    "dash",
    "seaborn",
    "flask",
    "requests",
    "aiohttp",
    "websockets",
    "markdown",
    "beautifulsoup4",
    "lxml",
    "html5lib",
    "jinja2",
]

# 排除的文件
excludes = [
    "tkinter",
    "unittest",
    "test",
    "tests",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
]

# 分析配置
a = Analysis(
    ['{config.main_script}'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 过滤掉不需要的文件
def filter_files(analysis):
    """过滤掉敏感和不需要的文件"""
    filtered_binaries = []
    filtered_datas = []
    
    # 过滤二进制文件
    for binary in analysis.binaries:
        include = True
        for exclude_pattern in {config.excluded_files}:
            if exclude_pattern in str(binary[0]):
                include = False
                break
        if include:
            filtered_binaries.append(binary)
    
    # 过滤数据文件
    for data in analysis.datas:
        include = True
        for exclude_pattern in {config.excluded_files}:
            if exclude_pattern in str(data[0]):
                include = False
                break
        if include:
            filtered_datas.append(data)
    
    analysis.binaries = filtered_binaries
    analysis.datas = filtered_datas
    return analysis

# 应用过滤
a = filter_files(a)

# PYZ配置
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 可执行文件配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{config.app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='uiLAYER/assets/bot.ico',  # 应用图标
    version='version_info.txt',  # 版本信息文件
)
