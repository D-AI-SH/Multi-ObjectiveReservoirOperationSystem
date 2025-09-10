from __future__ import annotations

"""Data Management Tab  ——  基于 QTreeWidget 的文件夹/文件树视图。

功能概述
---------
1. "水库文件夹" (reservoir folder) 作为树的根节点；其下子节点为：
   • 原始数据文件（内存 DataFrame）
   • 数据库表 (以 [DB] 开头)
2. 用户必须先选中一个水库文件夹节点，才能执行“加载临时文件 / 导入文件到数据库”。
3. 数据隔离：
   • 内存数据集 key 使用 "<alias>/<filename>"；alias 为文件夹 basename 经过下划线化处理。
   • 数据库表命名规则: "<alias>_<filename_noext>"。
4. 右键菜单：
   • 根节点：删除整个文件夹 (递归删除磁盘和数据库表，清理内存数据)。
   • 子节点：删除单个文件 / 数据库表。
"""

from pathlib import Path
import os
import shutil
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSplitter, QTreeWidget, QTableView, QTreeWidgetItem, QFileDialog, QInputDialog, QMessageBox
from .progress_dialog import ImportProgressDialog
from .import_worker import ImportWorker
from .icon_utils import load_icon
from .ui_utils import TRANSLATIONS
from .data_management.node_edit_mixin import NodeEditMixin
from .data_management import (
    alias_from_folder,
    db_table_name,
    BASE_DIR,
    TreeOpsMixin,
    ImportOpsMixin,
    DeleteOpsMixin,
    PreviewOpsMixin,
    AIConfigMixin,
)

# -----------------------------------------------------------------------------
#                               工具函数
# -----------------------------------------------------------------------------

def alias_from_folder(folder_path: str) -> str:
    """将文件夹路径转为安全 alias, 仅包含字母数字和下划线。"""
    base = Path(folder_path).name
    return base.replace(" ", "_").replace("-", "_")


def db_table_name(alias: str, file_name: str) -> str:
    """根据别名和文件名生成数据库表名。"""
    stem = Path(file_name).stem.replace(" ", "_").replace("-", "_")
    return f"{alias}_{stem}"


BASE_DIR = Path("data/reservoirs")

class DataManagementTab(
    QWidget,
    TreeOpsMixin,
    ImportOpsMixin,
    DeleteOpsMixin,
    PreviewOpsMixin,
    AIConfigMixin,
    NodeEditMixin,
):
    data_pool_updated = pyqtSignal()

    # ------------------------------------------------------------------
    # 初始化 / UI 构建
    # ------------------------------------------------------------------
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager

        # 确保基础数据目录存在
        BASE_DIR.mkdir(parents=True, exist_ok=True)

        # 管理状态
        self.reservoir_folders: list[str] = []
        self.current_folder_path: str | None = None  # 选中的水库文件夹
        self.folder_items: dict[str, QTreeWidgetItem] = {}

        self._init_ui()

        # 加载现有水库文件夹目录
        self._load_existing_root_folders()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # -------------------- 顶部按钮区 --------------------
        top_layout = QHBoxLayout()
        self.btn_add_folder = QPushButton("添加水库文件夹")
        self.btn_add_folder.setIcon(load_icon("folder.png", "folder"))
        self.btn_add_folder.clicked.connect(self.add_reservoir_folder)

        self.btn_load_temp = QPushButton("加载临时文件")
        self.btn_load_temp.setIcon(load_icon("open.png", "document-open"))
        self.btn_load_temp.clicked.connect(self.load_temp_file)

        self.btn_ai_config = QPushButton("AI配置")
        self.btn_ai_config.setIcon(load_icon("settings.png", "preferences-system"))
        self.btn_ai_config.clicked.connect(self.open_ai_config)

        top_layout.addWidget(self.btn_add_folder)
        top_layout.addWidget(self.btn_load_temp)
        top_layout.addWidget(self.btn_ai_config)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # -------------------- 主体：树 + 预览 ----------------
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # 直接在本类中定义上下文菜单处理方法，避免类型检查问题
        from .data_management.context_menu_mixin import ContextMenuMixin
        def _context_handler(pos):
            ContextMenuMixin.on_tree_context(self, pos)  # type: ignore[misc]
        self.tree_widget.customContextMenuRequested.connect(_context_handler)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        self.table_view = QTableView()

        splitter.addWidget(self.tree_widget)
        splitter.addWidget(self.table_view)
        splitter.setSizes([300, 700])

        main_layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # 文件夹增删 & 树刷新
    # ------------------------------------------------------------------
    def add_reservoir_folder(self):
        text, ok = QInputDialog.getText(self, "新水库文件夹", "输入文件夹名称：")
        if not ok or not text.strip():
            return
        name = text.strip()
        folder_path = (BASE_DIR / name).as_posix()
        if folder_path in self.reservoir_folders:
            self._select_folder_node(folder_path)
            return
        # 创建真实目录
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        self.reservoir_folders.append(folder_path)
        self._create_folder_node(folder_path)
        self._select_folder_node(folder_path)

    # 树构建逻辑由 TreeOpsMixin 提供

    def _load_existing_root_folders(self):
        """扫描 BASE_DIR 下已存在的文件夹并创建根节点"""
        for p in BASE_DIR.iterdir():
            if not p.is_dir():
                continue
            folder_path = p.as_posix()
            if folder_path not in self.reservoir_folders:
                self.reservoir_folders.append(folder_path)
                self._create_folder_node(folder_path)

    def _refresh_entire_tree(self):
        self.tree_widget.clear()
        self.folder_items.clear()
        for p in self.reservoir_folders:
            self._create_folder_node(p)

    # 兼容旧版本接口 —— 供 DataConfigTab 在数据链接变化时调用
    def refresh_data_list(self):
        """刷新当前文件夹节点（若选中）或整个树（无选中）。"""
        if self.current_folder_path:
            self._load_tree_from_db(self.current_folder_path)
        else:
            self._refresh_entire_tree()

    # ------------------------------------------------------------------
    # 右键菜单逻辑
    # ------------------------------------------------------------------
    # 右键菜单由 ContextMenuMixin 动态绑定

    # ------------------------------------------------------------------
    # 删除操作实现
    # ------------------------------------------------------------------
    # 删除相关逻辑由 DeleteOpsMixin 提供

    # 删除相关逻辑由 DeleteOpsMixin 提供

    # ---------------- 节点增删改 -------------------------
    # 节点新增/重命名由 NodeEditMixin 提供

    # 节点新增/重命名由 NodeEditMixin 提供

    # 导入相关逻辑由 ImportOpsMixin 提供

    # 导入相关逻辑由 ImportOpsMixin 提供

    # 删除相关逻辑由 DeleteOpsMixin 提供

    # ------------------------------------------------------------------
    # 加载/导入文件
    # ------------------------------------------------------------------
    # 校验当前文件夹由 ImportOpsMixin 提供

    # 临时文件加载由 ImportOpsMixin 提供

    def import_file(self):
        folder = self._require_current_folder()
        if folder is None:
            return
            
        files, _ = QFileDialog.getOpenFileNames(self, "选择导入文件", folder, "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if not files:
            return
            
        # 创建进度对话框
        progress_dialog = ImportProgressDialog(self, len(files))
        progress_dialog.canceled.connect(self._cancel_import)
        
        # 创建导入工作线程
        alias = alias_from_folder(folder)
        self.import_worker = ImportWorker(self.data_manager, files, folder, alias)
        
        # 连接信号
        self.import_worker.progress_updated.connect(progress_dialog.set_file_progress)
        self.import_worker.import_completed.connect(self._on_import_completed)
        self.import_worker.import_error.connect(self._on_import_error)
        
        # 保存对话框引用
        self.progress_dialog = progress_dialog
        
        # 启动导入
        self.import_worker.start()
        progress_dialog.exec()
        
    def _cancel_import(self):
        """取消导入"""
        if hasattr(self, 'import_worker'):
            self.import_worker.cancel()
            self.import_worker.wait()
            
    def _on_import_completed(self, success_count, total_count):
        """导入完成处理"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.set_import_complete(success_count, total_count)
            # 等待用户点击确定按钮，对话框会自动关闭
            
        # 刷新界面
        folder = self._require_current_folder()
        if folder:
            self._load_tree_from_db(folder)
        self.data_pool_updated.emit()
        
    def _on_import_error(self, error_message):
        """导入错误处理"""
        QMessageBox.warning(self, "导入错误", error_message)

    # ------------------------------------------------------------------
    # 树节点点击 -> 预览
    # ------------------------------------------------------------------
    # 预览逻辑由 PreviewOpsMixin 提供

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    # 预览辅助逻辑由 PreviewOpsMixin 提供

    # 预览辅助逻辑由 PreviewOpsMixin 提供
    
    # AI 配置逻辑由 AIConfigMixin 提供