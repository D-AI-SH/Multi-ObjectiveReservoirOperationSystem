from __future__ import annotations

from typing import Any
import os
import shutil
import gc
import time
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
        
        # 强制垃圾回收，释放可能的文件句柄
        gc.collect()
        
        # 删除磁盘文件夹
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 先尝试删除文件夹内的所有文件
                for root, dirs, files in os.walk(folder_path, topdown=False):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            # 确保文件不是只读
                            os.chmod(file_path, 0o777)
                            os.remove(file_path)
                        except Exception as file_e:
                            print(f"删除文件失败 {file_path}: {file_e}")
                    
                    for dir in dirs:
                        dir_path = os.path.join(root, dir)
                        try:
                            os.rmdir(dir_path)
                        except Exception as dir_e:
                            print(f"删除目录失败 {dir_path}: {dir_e}")
                
                # 最后删除主文件夹
                os.rmdir(folder_path)
                break  # 成功删除，退出重试循环
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"删除文件夹失败，尝试第 {attempt + 2} 次: {e}")
                    # 等待一段时间后重试，让系统有机会释放文件句柄
                    time.sleep(1)
                    gc.collect()
                else:
                    # 如果还是失败，尝试使用shutil.rmtree
                    try:
                        shutil.rmtree(folder_path)
                    except Exception as final_e:
                        QMessageBox.critical(
                            None, 
                            "删除失败", 
                            f"删除文件夹失败: {final_e}\n\n"
                            f"可能是因为某些文件正在被其他程序使用。\n"
                            f"请关闭所有相关程序后重试，或重启应用程序后再次尝试删除。"
                        )
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


