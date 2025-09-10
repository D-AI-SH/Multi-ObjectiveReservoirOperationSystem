from __future__ import annotations

from typing import Any
import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem
from PyQt6.QtCore import Qt

from .utils import alias_from_folder


class DeleteOpsMixin:
    data_manager: Any

    def _delete_folder(self, folder_path: str) -> None:
        reply = QMessageBox.question(
            None,
            "确认删除",
            f"删除文件夹将删除内部所有文件及数据库表，无法恢复。\n{folder_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        alias = alias_from_folder(folder_path)
        
        # 使用新的清理方法彻底清理所有相关数据
        self.data_manager.clear_all_data_for_alias(alias)
        
        # 删除磁盘文件夹
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            QMessageBox.critical(None, "删除失败", f"删除文件夹失败: {e}")
            return
        
        # 更新UI
        self.reservoir_folders.remove(folder_path)  # type: ignore[attr-defined]
        self._refresh_entire_tree()  # type: ignore[attr-defined]
        self.table_view.setModel(None)  # type: ignore[attr-defined]
        self.data_pool_updated.emit()  # type: ignore[attr-defined]

    def _delete_raw_dataset(self, key: str, file_path: str) -> None:
        if not self.data_manager.remove_raw_dataset(key):
            return
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"删除磁盘文件失败: {e}")
        self._load_tree_from_db(Path(file_path).parent.as_posix())  # type: ignore[attr-defined]
        self.table_view.setModel(None)  # type: ignore[attr-defined]
        self.data_pool_updated.emit()  # type: ignore[attr-defined]

    def _delete_virtual_node(self, item: QTreeWidgetItem) -> None:
        info = item.data(0, Qt.ItemDataRole.UserRole)
        if not info or info.get("type") != "vnode":
            return
        reply = QMessageBox.question(
            None,
            "确认删除",
            "删除节点将删除其所有子节点及绑定文件，无法恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.data_manager.delete_node(info["id"])
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            self.tree_widget.takeTopLevelItem(self.tree_widget.indexOfTopLevelItem(item))  # type: ignore[attr-defined]

    def _delete_db_table(self, table_name: str) -> None:
        if self.data_manager.delete_table(table_name):
            # 更新UI但不重新扫描文件夹
            alias = table_name.split("_", 1)[0]
            for folder in self.reservoir_folders:  # type: ignore[attr-defined]
                if alias_from_folder(folder) == alias:
                    # 只刷新当前文件夹的树结构，不重新扫描文件
                    self._refresh_folder_tree_only(folder)  # type: ignore[attr-defined]
                    break
            self.table_view.setModel(None)  # type: ignore[attr-defined]
        self.data_pool_updated.emit()  # type: ignore[attr-defined]


