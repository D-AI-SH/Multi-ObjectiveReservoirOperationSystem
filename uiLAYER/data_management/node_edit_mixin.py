from __future__ import annotations

from PyQt6.QtWidgets import QInputDialog, QTreeWidgetItem
from PyQt6.QtCore import Qt


class NodeEditMixin:
    def _add_child_node(self, parent_item: QTreeWidgetItem) -> None:
        text, ok = QInputDialog.getText(None, "新增节点", "节点名称：")
        if not ok or not text.strip():
            return
        parent_info = parent_item.data(0, Qt.ItemDataRole.UserRole)
        root_item = parent_item
        while root_item.parent() is not None:  # type: ignore[attr-defined]
            root_item = root_item.parent()  # type: ignore[attr-defined]
        root_info = root_item.data(0, Qt.ItemDataRole.UserRole)  # type: ignore[attr-defined]
        alias = root_info.get("alias", "")
        parent_id = parent_info["id"] if parent_info["type"] == "vnode" else None
        node_id = self.data_manager.add_node(alias, parent_id, text.strip())  # type: ignore[attr-defined]
        if node_id is None:
            return
        child = QTreeWidgetItem(parent_item, [text.strip()])
        child.setData(0, Qt.ItemDataRole.UserRole, {"type": "vnode", "id": node_id})
        parent_item.setExpanded(True)

    def _rename_node(self, item: QTreeWidgetItem) -> None:
        info = item.data(0, Qt.ItemDataRole.UserRole)
        if info["type"] not in ("vnode",):
            return
        text, ok = QInputDialog.getText(None, "重命名节点", "新名称：", text=item.text(0))
        if not ok or not text.strip():
            return
        item.setText(0, text.strip())
        self.data_manager.rename_node(info["id"], text.strip())  # type: ignore[attr-defined]


