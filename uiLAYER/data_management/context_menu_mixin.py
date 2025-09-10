from __future__ import annotations

from PyQt6.QtWidgets import QMenu, QWidget
from PyQt6.QtCore import Qt


class ContextMenuMixin(QWidget):
    def on_tree_context(self, pos):
        item = self.tree_widget.itemAt(pos)  # type: ignore[attr-defined]
        if item is None:
            return
        info = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(None)
        if info["type"] in ("folder", "vnode"):
            action_add = menu.addAction("新增子节点")
            action_add.triggered.connect(lambda: self._add_child_node(item))  # type: ignore[attr-defined]
            action_rename = menu.addAction("重命名节点")
            action_rename.triggered.connect(lambda: self._rename_node(item))  # type: ignore[attr-defined]
            if info["type"] == "vnode":
                action_import = menu.addAction("导入文件到此节点")
                action_import.triggered.connect(lambda: self._import_files_to_node(item))  # type: ignore[attr-defined]
            elif info["type"] == "folder":
                action_import = menu.addAction("导入文件到此文件夹")
                action_import.triggered.connect(lambda: self._import_files_to_folder(item))  # type: ignore[attr-defined]
            action_del = menu.addAction("删除节点" if info["type"] == "vnode" else "删除水库文件夹")
            if info["type"] == "vnode":
                action_del.triggered.connect(lambda: self._delete_virtual_node(item))  # type: ignore[attr-defined]
            else:
                action_del.triggered.connect(lambda: self._delete_folder(info["path"]))  # type: ignore[attr-defined]
        else:
            action_import = menu.addAction("导入文件到此文件夹")
            action_import.triggered.connect(lambda: self._import_files_to_folder(item))  # type: ignore[attr-defined]
            action_del = menu.addAction("删除数据")
            if info["type"] == "file":
                action_del.triggered.connect(lambda: self._delete_raw_dataset(info["key"], info["path"]))  # type: ignore[attr-defined]
            else:
                action_del.triggered.connect(lambda: self._delete_db_table(info["table"]))  # type: ignore[attr-defined]
        menu.exec(self.tree_widget.mapToGlobal(pos))  # type: ignore[attr-defined]


