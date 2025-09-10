from __future__ import annotations

from typing import Any
import pandas as pd  # type: ignore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from .utils import alias_from_folder


class PreviewOpsMixin:
    data_manager: Any

    def on_tree_item_clicked(self, item: QTreeWidgetItem) -> None:
        info = item.data(0, Qt.ItemDataRole.UserRole)
        if info["type"] in ("folder", "vnode"):
            self.table_view.setModel(None)  # type: ignore[attr-defined]
            return
        if info["type"] == "file":
            key = info["key"]
            df = self.data_manager.raw_datasets.get(key)
        else:
            table = info["table"]
            try:
                df = pd.read_sql_query(f'SELECT * FROM "{table}"', self.data_manager.db_conn)
            except Exception as e:  # pragma: no cover - UI 反馈
                print(e)
                df = None
        if df is not None:
            from ..ui_utils import PandasModel  # local import to avoid cycles
            self.table_view.setModel(PandasModel(df.head(200)))  # type: ignore[attr-defined]
        else:
            self.table_view.setModel(None)  # type: ignore[attr-defined]

    def _get_tables_for_alias(self, alias: str) -> list[str]:
        if not self.data_manager.db_conn:
            return []
        cur = self.data_manager.db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (f"{alias}_%",))
        return [r[0] for r in cur.fetchall()]

    def _get_or_create_root_node(self, alias: str) -> int:
        flat = self.data_manager.fetch_tree_flat(alias)
        for row in flat:
            node_id, parent_id, name, _ = row
            if parent_id is None and name == "(未分类)":
                return node_id
        return self.data_manager.add_node(alias, None, "(未分类)") or 0

    def _generate_file_tooltip(self, source_name: str) -> str:
        preview_text = "预览不可用"
        try:
            if source_name.startswith("[DB] "):
                table_name = source_name.replace("[DB] ", "")
                preview_df = self.data_manager.db_conn.execute(f'SELECT * FROM "{table_name}" LIMIT 5').fetchall()
                if preview_df:
                    cols = [desc[0] for desc in self.data_manager.db_conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0').description]
                    df = pd.DataFrame(preview_df, columns=cols)
                    preview_text = df.to_string(index=False, max_colwidth=20)
            else:
                df = self.data_manager.raw_datasets.get(source_name)
                if df is not None:
                    preview_text = df.head(5).to_string(index=False, max_colwidth=20)
        except Exception as e:
            preview_text = f"预览失败: {e}"
        return preview_text

    def _generate_column_tooltip(self, source_name: str, col_name: str) -> str:
        preview_text = "预览不可用"
        try:
            if source_name.startswith("[DB] "):
                table_name = source_name.replace("[DB] ", "")
                query = f'SELECT "{col_name}" FROM "{table_name}" LIMIT 5'
                df = pd.read_sql_query(query, self.data_manager.db_conn)
                preview_text = df.to_string(index=False, max_colwidth=20)
            else:
                df_full = self.data_manager.raw_datasets.get(source_name)
                if df_full is not None and col_name in df_full.columns:
                    preview_text = df_full[[col_name]].head(5).to_string(index=False, max_colwidth=20)
        except Exception as e:
            preview_text = f"预览失败: {e}"
        return preview_text


