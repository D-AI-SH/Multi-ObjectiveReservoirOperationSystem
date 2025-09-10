#!/usr/bin/env python3
"""
导入工作线程模块
提供后台文件导入功能，避免界面冻结
"""

import os
import shutil
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


class ImportWorker(QThread):
    """导入工作线程，用于后台处理文件导入"""
    
    # 信号定义
    progress_updated = pyqtSignal(int, str, str)  # file_index, file_name, status
    import_completed = pyqtSignal(int, int)  # success_count, total_count
    import_error = pyqtSignal(str)  # error_message
    
    def __init__(self, data_manager, files, folder_path, alias):
        super().__init__()
        self.data_manager = data_manager
        self.files = files
        self.folder_path = folder_path
        self.alias = alias
        self.is_cancelled = False
        
    def run(self):
        """执行导入任务"""
        success_count = 0
        total_count = len(self.files)
        
        try:
            for i, file_path in enumerate(self.files):
                if self.is_cancelled:
                    break
                    
                file_name = Path(file_path).name
                self.progress_updated.emit(i, file_name, "复制文件...")
                
                # 复制文件到目标文件夹
                dest_path = Path(self.folder_path) / file_name
                if os.path.abspath(file_path) != dest_path.as_posix():
                    shutil.copy2(file_path, dest_path)
                
                self.progress_updated.emit(i, file_name, "导入到数据库...")
                
                # 导入到数据库
                try:
                    table_name = self.data_manager.import_file_to_db(dest_path.as_posix(), self.alias)
                    if table_name:
                        success_count += 1
                        print(f"数据库表已导入: {table_name}")
                    else:
                        print(f"导入失败: {file_name}")
                except Exception as e:
                    print(f"导入文件 '{file_name}' 时发生错误: {e}")
                    self.import_error.emit(f"导入文件 '{file_name}' 失败: {str(e)}")
                    
            # 发送完成信号
            self.import_completed.emit(success_count, total_count)
            
        except Exception as e:
            self.import_error.emit(f"导入过程中发生错误: {str(e)}")
            
    def cancel(self):
        """取消导入任务"""
        self.is_cancelled = True
