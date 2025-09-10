from __future__ import annotations

from typing import Any
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from .utils import alias_from_folder


class TreeOpsMixin:
    tree_widget: Any
    data_manager: Any
    folder_items: dict[str, QTreeWidgetItem]

    def _create_folder_node(self, folder_path: str) -> None:
        alias = alias_from_folder(folder_path)
        display_name = Path(folder_path).name
        parent_item = QTreeWidgetItem(self.tree_widget, [display_name])
        parent_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "path": folder_path, "alias": alias})
        self.folder_items[folder_path] = parent_item
        parent_item.setExpanded(True)
        self._load_tree_from_db(folder_path)

    def _select_folder_node(self, folder_path: str) -> None:
        item = self.folder_items.get(folder_path)
        if item:
            self.current_folder_path = folder_path  # type: ignore[attr-defined]
            self.tree_widget.setCurrentItem(item)

    def _load_tree_from_db(self, folder_path: str) -> None:
        parent_item = self.folder_items.get(folder_path)
        if parent_item is None:
            return
        parent_item.takeChildren()
        alias = alias_from_folder(folder_path)

        def create_nodes(parent_qitem: QTreeWidgetItem, vnodes: list[dict]) -> None:
            for node in vnodes:
                item = QTreeWidgetItem(parent_qitem, [node["name"]])
                item.setData(0, Qt.ItemDataRole.UserRole, {"type": "vnode", "id": node["id"]})
                for fk in self.data_manager.get_files_for_node(node["id"]):
                    if fk.startswith("[DB] "):
                        child = QTreeWidgetItem(item, [fk])
                        child.setData(0, Qt.ItemDataRole.UserRole, {"type": "db", "table": fk.replace("[DB] ", "")})
                    else:
                        child = QTreeWidgetItem(item, [Path(fk).name])
                        child.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "key": fk, "path": str(Path(folder_path)/Path(fk).name)})
                create_nodes(item, node["children"])

        vtree = self.data_manager.fetch_tree_hierarchy(alias)
        create_nodes(parent_item, vtree)
        parent_item.setExpanded(True)

    def _refresh_folder_tree_only(self, folder_path: str) -> None:
        """只刷新文件夹的树结构，不重新扫描文件"""
        parent_item = self.folder_items.get(folder_path)
        if parent_item is None:
            return
        
        # 清除现有子节点
        parent_item.takeChildren()
        alias = alias_from_folder(folder_path)

        def create_nodes(parent_qitem: QTreeWidgetItem, vnodes: list[dict]) -> None:
            for node in vnodes:
                item = QTreeWidgetItem(parent_qitem, [node["name"]])
                item.setData(0, Qt.ItemDataRole.UserRole, {"type": "vnode", "id": node["id"]})
                for fk in self.data_manager.get_files_for_node(node["id"]):
                    if fk.startswith("[DB] "):
                        child = QTreeWidgetItem(item, [fk])
                        child.setData(0, Qt.ItemDataRole.UserRole, {"type": "db", "table": fk.replace("[DB] ", "")})
                    else:
                        child = QTreeWidgetItem(item, [Path(fk).name])
                        child.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "key": fk, "path": str(Path(folder_path)/Path(fk).name)})
                create_nodes(item, node["children"])

        # 只从数据库获取现有数据，不扫描文件
        vtree = self.data_manager.fetch_tree_hierarchy(alias)
        create_nodes(parent_item, vtree)
        parent_item.setExpanded(True)


