from __future__ import annotations

from typing import Any
from pathlib import Path
import os
import shutil
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem
from PyQt6.QtCore import Qt

from .utils import alias_from_folder


class ImportOpsMixin:
    data_manager: Any

    def _require_current_folder(self) -> str | None:
        if not getattr(self, "current_folder_path", None):  # type: ignore[attr-defined]
            QMessageBox.warning(None, "未选择水库文件夹", "请先左侧选择一个水库文件夹节点。")
            return None
        return self.current_folder_path  # type: ignore[attr-defined]

    def _import_files_to_node(self, vnode_item: QTreeWidgetItem) -> None:
        info = vnode_item.data(0, Qt.ItemDataRole.UserRole)
        node_id = info["id"]
        root_item = vnode_item
        while root_item.parent() is not None:  # type: ignore[attr-defined]
            root_item = root_item.parent()  # type: ignore[attr-defined]
        root_info = root_item.data(0, Qt.ItemDataRole.UserRole)  # type: ignore[attr-defined]
        folder_path = root_info["path"]
        alias = root_info["alias"]
        files, _ = QFileDialog.getOpenFileNames(None, "选择导入文件", folder_path, "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if not files:
            return
        for f in files:
            dest = Path(folder_path) / Path(f).name
            if os.path.abspath(f) != dest.as_posix():
                try:
                    shutil.copy2(f, dest)
                except PermissionError:
                    QMessageBox.warning(None, "文件占用", f"{f} 被占用，无法复制，已跳过。")
                    continue
            table_name = self.data_manager.import_file_to_db(dest.as_posix(), alias)
            if not table_name:
                continue
            fk = f"[DB] {table_name}"
            self.data_manager.bind_file(node_id, fk)
            child = QTreeWidgetItem(vnode_item, [fk])
            child.setData(0, Qt.ItemDataRole.UserRole, {"type": "db", "table": table_name})
        vnode_item.setExpanded(True)
        self.data_pool_updated.emit()  # type: ignore[attr-defined]

    def _import_files_to_folder(self, folder_item: QTreeWidgetItem) -> None:
        info = folder_item.data(0, Qt.ItemDataRole.UserRole)  # type: ignore[attr-defined]
        folder_path = info["path"]
        alias = info["alias"]
        files, _ = QFileDialog.getOpenFileNames(None, "选择导入文件", folder_path, "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if not files:
            return
        root_node_id = self._get_or_create_root_node(alias)  # type: ignore[attr-defined]
        for f in files:
            dest = Path(folder_path) / Path(f).name
            if os.path.abspath(f) != dest.as_posix():
                try:
                    shutil.copy2(f, dest)
                except PermissionError:
                    QMessageBox.warning(None, "文件占用", f"{f} 被占用，无法复制，已跳过。")
                    continue
            table_name = self.data_manager.import_file_to_db(dest.as_posix(), alias)
            if not table_name:
                continue
            fk = f"[DB] {table_name}"
            self.data_manager.bind_file(root_node_id, fk)
        self._load_tree_from_db(folder_path)  # type: ignore[attr-defined]
        self.data_pool_updated.emit()  # type: ignore[attr-defined]

    def load_temp_file(self) -> None:
        folder = self._require_current_folder()
        if folder is None:
            return
        files, _ = QFileDialog.getOpenFileNames(None, "选择临时文件", folder, "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if not files:
            return
        alias = alias_from_folder(folder)
        for f in files:
            dest = Path(folder) / Path(f).name
            if os.path.abspath(f) != dest.as_posix():
                shutil.copy2(f, dest)
            name, df = self.data_manager.load_raw_dataset(dest.as_posix())
            if df is None:
                continue
            key_old = name
            key_new = f"{alias}/{name}"
            self.data_manager.raw_datasets[key_new] = self.data_manager.raw_datasets.pop(key_old)
        self._load_tree_from_db(folder)  # type: ignore[attr-defined]
        self.data_pool_updated.emit()  # type: ignore[attr-defined]


