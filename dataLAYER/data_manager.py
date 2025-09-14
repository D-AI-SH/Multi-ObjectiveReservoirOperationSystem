import pandas as pd  # type: ignore
import os
import sqlite3
import warnings
from typing import Dict
from .smart_data_processor import SmartDataProcessor  # type: ignore
from .mixins import FileIOMixin  # type: ignore

# 忽略 pandas 读取某些Excel文件时可能产生的格式警告
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

class DataManager(FileIOMixin):
    DB_FILE = "data/project_database.db"

    def __init__(self, ai_enabled: bool = False):
        # 1. 确保数据库文件夹存在并建立连接
        os.makedirs(os.path.dirname(self.DB_FILE), exist_ok=True)
        try:
            self.db_conn = sqlite3.connect(self.DB_FILE)
            self.db_conn.execute("PRAGMA foreign_keys = ON;")
            print(f"成功连接到数据库: {self.DB_FILE}")
        except sqlite3.Error as e:
            self.db_conn = None
            print(f"数据库连接失败: {e}")

        # 2. AI配置初始化
        self.ai_enabled = ai_enabled
        self.ai_api_key = ""
        self.ai_api_url = "https://api.ai-assistant.com/v1/chat/completions"
        self.ai_model = "gpt-3.5-turbo"
        
        # 3. 初始化智能数据处理器
        self.smart_processor = SmartDataProcessor(self.db_conn, ai_enabled)
        
        # 4. 初始化内存结构
        self.raw_datasets = {}
        self.data_links = {}
        self.multi_reservoir_data_links = {}  # 多水库数据链接
        self.multi_reservoir_results = {}  # 多水库结果数据
        self.date_range_filter = None  # 日期范围过滤器
        self.interpolated_data = {}  # 插值数据

        # 5. 初始化树形节点表
        self._init_tree_tables()
        
        # 6. 启动时检查数据库日期列
        self._check_database_on_startup()

    # 文件读取等逻辑已迁移至 FileIOMixin._read_file_robustly

    def _check_database_on_startup(self):
        """启动时检查数据库中的日期列"""
        if not self.db_conn:
            return
            
        # 检查是否需要启动时检查
        if not self._should_check_database_on_startup():
            print("数据库已优化，跳过启动时检查")
            return
            
        print("正在检查数据库中的日期列...")
        result = self.smart_processor.check_and_fix_database_dates()
        if result['status'] == 'success':
            print(f"数据库检查完成: 检查了 {result['tables_checked']} 个表，修复了 {result['tables_fixed']} 个表")
            if result['details']:
                for detail in result['details']:
                    print(f"  - 表 '{detail['table']}': {detail['action']}")
            
            # 标记数据库已优化
            self._mark_database_optimized()
        else:
            print(f"数据库检查失败: {result['message']}")
    
    def _should_check_database_on_startup(self) -> bool:
        """检查是否需要在启动时检查数据库"""
        try:
            conn = self.db_conn
            if conn is None:
                return True
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='system_metadata'
            """)
            
            if not cursor.fetchone():
                # 如果系统元数据表不存在，需要检查
                return True
            
            # 检查数据库优化标记
            cursor.execute("""
                SELECT value FROM system_metadata 
                WHERE key='database_optimized'
            """)
            
            result = cursor.fetchone()
            if result and result[0] == 'true':
                return False
            else:
                return True
                
        except Exception as e:
            print(f"检查数据库优化状态时出错: {e}")
            return True  # 出错时默认检查
    
    def _mark_database_optimized(self):
        """标记数据库已优化"""
        try:
            conn = self.db_conn
            if conn is None:
                return
            cursor = conn.cursor()
            
            # 创建系统元数据表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入或更新优化标记
            cursor.execute("""
                INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
                VALUES ('database_optimized', 'true', CURRENT_TIMESTAMP)
            """)
            
            conn.commit()
            print("数据库优化状态已记录")
            
        except Exception as e:
            print(f"记录数据库优化状态时出错: {e}")
    
    def mark_database_needs_check(self):
        """标记数据库需要重新检查（当数据被编辑时调用）"""
        try:
            conn = self.db_conn
            if conn is None:
                return
            cursor = conn.cursor()
            
            # 创建系统元数据表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 清除优化标记
            cursor.execute("""
                INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
                VALUES ('database_optimized', 'false', CURRENT_TIMESTAMP)
            """)
            
            conn.commit()
            print("数据库标记为需要重新检查")
            
        except Exception as e:
            print(f"标记数据库需要检查时出错: {e}")

    def load_raw_dataset(self, file_path):
        """加载一个原始数据文件到内存数据池中。"""
        try:
            filename = os.path.basename(file_path)
            data = self._read_file_robustly(file_path)
            if data is None:
                return None, None # 读取失败
            
            # 智能处理日期列
            data = self.smart_processor.process_dataframe_dates(data)
            
            # 分析列名并提供建议
            column_analysis = self.smart_processor.get_column_analysis(data.columns.tolist())
            if column_analysis['suggestions']:
                print(f"数据列分析建议:")
                for suggestion in column_analysis['suggestions']:
                    print(f"  - {suggestion}")
            
            self.raw_datasets[filename] = data
            print(f"成功加载临时数据集 '{filename}' 到内存。")
            return filename, data
        except Exception as e:
            print(f"加载临时数据时发生错误: {e}")
            return None, None

    def import_file_to_db(self, file_path, table_prefix: str | None = None):
        """将数据文件作为一个新表导入到数据库中。"""
        if not self.db_conn:
            print("错误：数据库未连接。")
            return None
        try:
            table_name = os.path.splitext(os.path.basename(file_path))[0].replace('-', '_').replace(' ', '_')
            if table_prefix:
                table_name = f"{table_prefix}_{table_name}"
            data = self._read_file_robustly(file_path)
            if data is None:
                return None # 读取失败
            
            # 智能处理日期列
            data = self.smart_processor.process_dataframe_dates(data)
            
            # 分析列名并提供建议
            column_analysis = self.smart_processor.get_column_analysis(data.columns.tolist())
            if column_analysis['suggestions']:
                print(f"数据列分析建议:")
                for suggestion in column_analysis['suggestions']:
                    print(f"  - {suggestion}")
            
            data.to_sql(table_name, self.db_conn, if_exists='replace', index=False)
            print(f"成功将文件 '{os.path.basename(file_path)}' 导入到数据库表 '{table_name}'。")
            
            # 标记数据库需要重新检查（因为新数据被导入）
            self.mark_database_needs_check()
            
            return table_name
        except Exception as e:
            print(f"导入文件到数据库时发生错误: {e}")
            return None

    def delete_table(self, table_name):
        """从数据库删除指定表，并清理相关的数据链接。"""
        if not self.db_conn:
            print("错误：数据库未连接。")
            return False
        try:
            cursor = self.db_conn.cursor()
            
            # 删除数据库表
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            
            # 清理 node_files 表中与该表相关的记录
            cursor.execute("DELETE FROM node_files WHERE file_key = ?", (f"[DB] {table_name}",))
            deleted_links = cursor.rowcount
            if deleted_links > 0:
                print(f"已清理 {deleted_links} 个节点文件关联记录")
            
            self.db_conn.commit()
            print(f"成功删除数据库表 '{table_name}'。")

            # 清理单水库数据链接
            to_remove = [req_id for req_id, (src_name, _) in self.data_links.items() if src_name == f"[DB] {table_name}"]
            for req_id in to_remove:
                del self.data_links[req_id]
                print(f"已移除与被删除表关联的数据链接: {req_id}")
            
            # 清理多水库数据链接
            if hasattr(self, 'multi_reservoir_data_links'):
                multi_to_remove = []
                for link_key, (src_name, _) in self.multi_reservoir_data_links.items():
                    if src_name == f"[DB] {table_name}":
                        multi_to_remove.append(link_key)
                
                for link_key in multi_to_remove:
                    del self.multi_reservoir_data_links[link_key]
                    print(f"已移除与被删除表关联的多水库数据链接: {link_key}")
            
            return True
        except Exception as e:
            print(f"从数据库删除表 '{table_name}' 失败: {e}")
            return False

    def remove_raw_dataset(self, filename):
        """从内存池删除临时数据集，并清理相关数据链接。"""
        if filename in self.raw_datasets:
            del self.raw_datasets[filename]
            # 清理指向该文件的单水库数据链接
            to_remove = [req_id for req_id, (src_name, _) in self.data_links.items() if src_name == filename]
            for req_id in to_remove:
                del self.data_links[req_id]
                print(f"已移除与被删除临时数据集关联的数据链接: {req_id}")
            
            # 清理指向该文件的多水库数据链接
            if hasattr(self, 'multi_reservoir_data_links'):
                multi_to_remove = []
                for link_key, (src_name, _) in self.multi_reservoir_data_links.items():
                    if src_name == filename:
                        multi_to_remove.append(link_key)
                
                for link_key in multi_to_remove:
                    del self.multi_reservoir_data_links[link_key]
                    print(f"已移除与被删除临时数据集关联的多水库数据链接: {link_key}")
            
            print(f"成功删除临时数据集 '{filename}'。")
            return True
        print(f"错误：未找到临时数据集 '{filename}'。")
        return False

    def get_all_data_source_names(self):
        """获取所有数据源的名称（内存文件 + 数据库表）。"""
        sources = list(self.raw_datasets.keys())
        if self.db_conn:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [f"[DB] {table[0]}" for table in cursor.fetchall()]
            sources.extend(tables)
        return sources

    def get_source_columns(self, source_name):
        """根据数据源名称（内存或数据库）获取其列名。"""
        columns = []
        if source_name.startswith("[DB] "):
            table_name = source_name.replace("[DB] ", "")
            try:
                # 使用pandas读取表结构以简化列名获取
                df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", self.db_conn)
                columns = df.columns.tolist()
            except Exception as e:
                print(f"从数据库表 '{table_name}' 获取列名时出错: {e}")
                return []
        else:
            dataset = self.raw_datasets.get(source_name)
            if dataset is not None:
                columns = dataset.columns.tolist()
        
        return columns

    def get_smart_column_matches(self, source_name: str) -> Dict[str, str]:
        """获取智能列名匹配和翻译"""
        columns = self.get_source_columns(source_name)
        if not columns:
            return {}
        
        return self.smart_processor.smart_column_matching(columns)

    def set_data_link(self, requirement_id, source_name, source_column):
        """设置数据链接。"""
        self.data_links[requirement_id] = (source_name, source_column)
        print(f"数据链接已更新: '{requirement_id}' -> '{source_name}'[{source_column}]")

    def get_model_input_data(self, required_ids):
        """根据数据链接，为模型准备最终的输入数据。"""
        model_input = {}
        first_df_index = None

        for req_id in required_ids:
            link = self.data_links.get(req_id)
            if not link:
                print(f"错误：数据链接 '{req_id}' 尚未配置。")
                return None
            
            source_name, col_name = link
            
            if source_name.startswith("[DB] "):
                table_name = source_name.replace("[DB] ", "")
                try:
                    source_df = pd.read_sql_query(f"SELECT \"{col_name}\" FROM \"{table_name}\"", self.db_conn)
                except Exception as e:
                    print(f"从数据库读取表 '{table_name}' 的列 '{col_name}' 失败: {e}")
                    return None
            else:
                source_df_full = self.raw_datasets.get(source_name)
                if source_df_full is None:
                    print(f"错误：链接所需的数据源 '{source_name}' 不存在。")
                    return None
                if col_name not in source_df_full.columns:
                    print(f"错误：链接所需的列 '{col_name}' 在数据源 '{source_name}' 中不存在。")
                    return None
                source_df = source_df_full[[col_name]].copy()

            # 检查索引是否一致
            if first_df_index is None:
                first_df_index = source_df.index
            elif not first_df_index.equals(source_df.index):
                print(f"警告：数据源 '{source_name}' 的数据长度与其它数据源不一致，可能导致合并问题。")

            model_input[req_id] = source_df.rename(columns={col_name: req_id})
            
        if not model_input:
            return None
        
        # 使用 reset_index()...set_index() 强制对齐
        final_df = pd.concat([df.reset_index(drop=True) for df in model_input.values()], axis=1)
        
        return final_df

    def __del__(self):
        """确保在程序退出时关闭数据库连接。"""
        if self.db_conn:
            self.db_conn.close()
            print("数据库连接已关闭。")

    # ------------------------------------------------------------------
    # 树形数据库相关 API
    # ------------------------------------------------------------------
    def _init_tree_tables(self):
        """确保 tree_nodes 与 node_files 两张表存在"""
        if not self.db_conn:
            return
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tree_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alias TEXT NOT NULL,
                parent_id INTEGER,
                name TEXT NOT NULL,
                order_idx INTEGER DEFAULT 0,
                FOREIGN KEY(parent_id) REFERENCES tree_nodes(id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS node_files (
                node_id INTEGER NOT NULL REFERENCES tree_nodes(id) ON DELETE CASCADE,
                file_key TEXT NOT NULL,
                UNIQUE(node_id, file_key)
            );
            """
        )
        self.db_conn.commit()

    # --- 节点 CRUD ------------------------------------------------------
    def add_node(self, alias: str, parent_id: int | None, name: str) -> int | None:
        if not self.db_conn:
            return None
        cursor = self.db_conn.cursor()
        cursor.execute(
            "INSERT INTO tree_nodes(alias, parent_id, name, order_idx) VALUES(?,?,?,?)",
            (alias, parent_id, name, 0),
        )
        self.db_conn.commit()
        return cursor.lastrowid

    def rename_node(self, node_id: int, new_name: str):
        if not self.db_conn:
            return
        cursor = self.db_conn.cursor()
        cursor.execute("UPDATE tree_nodes SET name=? WHERE id=?", (new_name, node_id))
        self.db_conn.commit()

    def delete_node(self, node_id: int):
        """删除树节点，并清理相关的文件绑定和数据链接"""
        if not self.db_conn:
            return
        
        try:
            # 获取节点信息
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT alias FROM tree_nodes WHERE id=?", (node_id,))
            result = cursor.fetchone()
            if not result:
                print(f"未找到节点ID: {node_id}")
                return
            
            alias = result[0]
            
            # 获取该节点绑定的所有文件
            bound_files = self.get_files_for_node(node_id)
            
            # 清理相关的数据链接
            for file_key in bound_files:
                # 清理单水库数据链接
                to_remove = [req_id for req_id, (src_name, _) in self.data_links.items() if src_name == file_key]
                for req_id in to_remove:
                    del self.data_links[req_id]
                    print(f"已移除与删除节点关联的数据链接: {req_id}")
                
                # 清理多水库数据链接
                if hasattr(self, 'multi_reservoir_data_links'):
                    multi_to_remove = []
                    for link_key, (src_name, _) in self.multi_reservoir_data_links.items():
                        if src_name == file_key:
                            multi_to_remove.append(link_key)
                    
                    for link_key in multi_to_remove:
                        del self.multi_reservoir_data_links[link_key]
                        print(f"已移除与删除节点关联的多水库数据链接: {link_key}")
            
            # 删除节点文件绑定
            self.db_conn.execute("DELETE FROM node_files WHERE node_id=?", (node_id,))
            
            # 删除节点本身
            self.db_conn.execute("DELETE FROM tree_nodes WHERE id=?", (node_id,))
            
            self.db_conn.commit()
            print(f"成功删除节点ID: {node_id}，并清理了相关数据链接")
            
        except Exception as e:
            print(f"删除节点失败: {e}")
            self.db_conn.rollback()

    def move_node(self, node_id: int, new_parent_id: int | None, new_order: int = 0):
        if not self.db_conn:
            return
        self.db_conn.execute(
            "UPDATE tree_nodes SET parent_id=?, order_idx=? WHERE id=?",
            (new_parent_id, new_order, node_id),
        )
        self.db_conn.commit()

    def clear_multi_reservoir_data_links(self, source_name: str | None = None):
        """
        清理多水库数据链接
        
        Args:
            source_name: 如果指定，只清理指向该数据源的链接；否则清理所有链接
        """
        if not hasattr(self, 'multi_reservoir_data_links'):
            return
        
        if source_name:
            # 清理指定数据源的链接
            to_remove = []
            for link_key, (src_name, _) in self.multi_reservoir_data_links.items():
                if src_name == source_name:
                    to_remove.append(link_key)
            
            for link_key in to_remove:
                del self.multi_reservoir_data_links[link_key]
                print(f"已清理多水库数据链接: {link_key}")
        else:
            # 清理所有链接
            count = len(self.multi_reservoir_data_links)
            self.multi_reservoir_data_links.clear()
            print(f"已清理所有多水库数据链接，共 {count} 个")

    def set_multi_reservoir_data_link(self, reservoir_id: int, requirement_id: str, source_name: str, source_column: str):
        """
        设置多水库数据链接
        
        Args:
            reservoir_id: 水库ID
            requirement_id: 需求ID
            source_name: 数据源名称
            source_column: 数据源列名
        """
        if not hasattr(self, 'multi_reservoir_data_links'):
            self.multi_reservoir_data_links = {}
        
        link_key = f"{reservoir_id}_{requirement_id}"
        self.multi_reservoir_data_links[link_key] = (source_name, source_column)
        print(f"已设置多水库数据链接: {link_key} -> {source_name}[{source_column}]")

    def remove_multi_reservoir_data_link(self, reservoir_id: int, requirement_id: str):
        """
        移除多水库数据链接
        
        Args:
            reservoir_id: 水库ID
            requirement_id: 需求ID
        """
        if not hasattr(self, 'multi_reservoir_data_links'):
            return
        
        link_key = f"{reservoir_id}_{requirement_id}"
        if link_key in self.multi_reservoir_data_links:
            del self.multi_reservoir_data_links[link_key]
            print(f"已移除多水库数据链接: {link_key}")

    def clear_all_data_for_alias(self, alias: str):
        """
        清理指定别名相关的所有数据
        
        Args:
            alias: 水库别名
        """
        print(f"开始清理别名 '{alias}' 相关的所有数据...")
        
        # 1. 清理数据库表
        if self.db_conn:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (f"{alias}_%",))
                tables = [row[0] for row in cursor.fetchall()]
                
                for table_name in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                    print(f"已删除数据库表: {table_name}")
                
                self.db_conn.commit()
            except Exception as e:
                print(f"清理数据库表时出错: {e}")
        
        # 2. 清理内存中的原始数据集
        keys_to_remove = [key for key in self.raw_datasets.keys() if key.startswith(f"{alias}/")]
        for key in keys_to_remove:
            # 确保DataFrame被正确释放
            if key in self.raw_datasets:
                df = self.raw_datasets[key]
                if df is not None:
                    # 尝试释放DataFrame的内存
                    try:
                        del df
                    except:
                        pass
                del self.raw_datasets[key]
                print(f"已删除内存数据集: {key}")
        
        # 强制垃圾回收释放内存
        import gc
        gc.collect()
        
        # 3. 清理单水库数据链接
        links_to_remove = []
        for req_id, (src_name, _) in self.data_links.items():
            if src_name.startswith(f"{alias}/") or (src_name.startswith("[DB] ") and src_name.replace("[DB] ", "").startswith(f"{alias}_")):
                links_to_remove.append(req_id)
        
        for req_id in links_to_remove:
            del self.data_links[req_id]
            print(f"已删除数据链接: {req_id}")
        
        # 4. 清理多水库数据链接
        if hasattr(self, 'multi_reservoir_data_links'):
            multi_links_to_remove = []
            for link_key, (src_name, _) in self.multi_reservoir_data_links.items():
                if src_name.startswith(f"{alias}/") or (src_name.startswith("[DB] ") and src_name.replace("[DB] ", "").startswith(f"{alias}_")):
                    multi_links_to_remove.append(link_key)
            
            for link_key in multi_links_to_remove:
                del self.multi_reservoir_data_links[link_key]
                print(f"已删除多水库数据链接: {link_key}")
        
        # 5. 清理树节点
        if self.db_conn:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("DELETE FROM tree_nodes WHERE alias=?", (alias,))
                cursor.execute("DELETE FROM node_files WHERE node_id NOT IN (SELECT id FROM tree_nodes)")
                self.db_conn.commit()
                print(f"已清理别名 '{alias}' 的树节点")
            except Exception as e:
                print(f"清理树节点时出错: {e}")
        
        print(f"别名 '{alias}' 相关的所有数据清理完成")

    # --- 文件绑定 -------------------------------------------------------
    def bind_file(self, node_id: int, file_key: str):
        if not self.db_conn:
            return
        try:
            self.db_conn.execute(
                "INSERT OR IGNORE INTO node_files(node_id, file_key) VALUES(?,?)",
                (node_id, file_key),
            )
            self.db_conn.commit()
        except Exception as e:
            print(f"绑定文件失败: {e}")

    def unbind_file(self, node_id: int, file_key: str):
        if not self.db_conn:
            return
        self.db_conn.execute(
            "DELETE FROM node_files WHERE node_id=? AND file_key=?", (node_id, file_key)
        )
        self.db_conn.commit()

    def get_files_for_node(self, node_id: int) -> list[str]:
        if not self.db_conn:
            return []
        cur = self.db_conn.cursor()
        cur.execute("SELECT file_key FROM node_files WHERE node_id=?", (node_id,))
        return [r[0] for r in cur.fetchall()]

    # --- 取树 -----------------------------------------------------------
    def fetch_tree_flat(self, alias: str):
        if not self.db_conn:
            return []
        cur = self.db_conn.cursor()
        cur.execute(
            "SELECT id, parent_id, name, order_idx FROM tree_nodes WHERE alias=? ORDER BY order_idx, id",
            (alias,),
        )
        rows = cur.fetchall()
        return rows

    def fetch_tree_hierarchy(self, alias: str):
        """返回嵌套结构 [{'id':..., 'name':..., 'children': [...]}]"""
        flat = self.fetch_tree_flat(alias)
        nodes = {row[0]: {"id": row[0], "parent_id": row[1], "name": row[2], "children": []} for row in flat}
        roots = []
        for n in nodes.values():
            pid = n["parent_id"]
            if pid and pid in nodes:
                nodes[pid]["children"].append(n)
            else:
                roots.append(n)
        return roots

    def get_multi_reservoir_input_data(self, required_ids, reservoir_count):
        """
        获取多水库模型输入数据
        
        Args:
            required_ids: 模型需要的数据字段列表
            reservoir_count: 水库数量
            
        Returns:
            dict: {reservoir_id: DataFrame} 或 None
        """
        try:
            reservoir_data = {}
            
            for reservoir_id in range(1, reservoir_count + 1):
                # 检查该水库的所有必需数据链接是否完整
                missing_links = []
                for req_id in required_ids:
                    link_key = f"{reservoir_id}_{req_id}"
                    if link_key not in self.multi_reservoir_data_links:
                        missing_links.append(req_id)
                
                if missing_links:
                    print(f"水库 {reservoir_id} 缺少以下数据链接: {missing_links}")
                    continue
                
                # 构建该水库的数据
                reservoir_df_parts = []
                date_column = None
                
                for req_id in required_ids:
                    link_key = f"{reservoir_id}_{req_id}"
                    source_name, col_name = self.multi_reservoir_data_links[link_key]
                    
                    # 检查是否有插值数据
                    if link_key in self.interpolated_data:
                        print(f"使用插值数据: {link_key}")
                        interpolated_info = self.interpolated_data[link_key]
                        col_data = interpolated_info['interpolated_data'][col_name]
                    else:
                        # 获取原始数据
                        if source_name.startswith("[DB] "):
                            table_name = source_name.replace("[DB] ", "")
                            query = f'SELECT "{col_name}" FROM "{table_name}"'
                            col_data = pd.read_sql_query(query, self.db_conn)[col_name]
                        else:
                            if source_name not in self.raw_datasets:
                                print(f"未找到数据源: {source_name}")
                                continue
                            col_data = self.raw_datasets[source_name][col_name]
                    
                    # 检查是否为日期列（第一个非空的列）
                    if date_column is None and not col_data.empty:
                        try:
                            # 尝试转换为日期类型
                            test_date = pd.to_datetime(col_data.iloc[0], errors='coerce')
                            if pd.notna(test_date):
                                date_column = col_name
                        except:
                            pass
                    
                    # 重命名列为标准名称
                    col_df = pd.DataFrame({req_id: col_data})
                    # 确保col_df是有效的DataFrame
                    if not col_df.empty and col_df.shape[1] == 1:
                        reservoir_df_parts.append(col_df)
                    else:
                        print(f"警告: 跳过无效的DataFrame: {req_id}, 形状: {col_df.shape}")
                
                if reservoir_df_parts:
                    # 合并所有列
                    reservoir_df = pd.concat(reservoir_df_parts, axis=1)
                    
                    # 应用日期过滤器（如果设置了的话）
                    if self.date_range_filter and date_column:
                        reservoir_df = self.apply_date_filter_to_data(reservoir_df, date_column)
                    
                    reservoir_data[reservoir_id] = reservoir_df
                    print(f"水库 {reservoir_id} 数据准备完成，形状: {reservoir_df.shape}")
            
            return reservoir_data if reservoir_data else None
            
        except Exception as e:
            print(f"获取多水库输入数据时出错: {e}")
            return None

    def store_multi_reservoir_results(self, results_dict):
        """
        存储多水库计算结果
        
        Args:
            results_dict: {reservoir_id: DataFrame} 或 {data_type: DataFrame}
        """
        if isinstance(results_dict, dict):
            self.multi_reservoir_results.update(results_dict)
        else:
            print("结果数据格式错误，应为字典类型")

    def get_multi_reservoir_results(self):
        """获取多水库结果数据"""
        return self.multi_reservoir_results
    
    def set_date_range_filter(self, start_date, end_date):
        """
        设置日期范围过滤器
        
        Args:
            start_date: 开始日期字符串 (YYYY-MM-DD)
            end_date: 结束日期字符串 (YYYY-MM-DD)
        """
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            self.date_range_filter = {
                'start': start_dt,
                'end': end_dt
            }
            print(f"日期范围过滤器已设置: {start_date} 至 {end_date}")
        except Exception as e:
            print(f"设置日期范围过滤器失败: {e}")
            self.date_range_filter = None
    
    def get_date_range_filter(self):
        """获取当前日期范围过滤器"""
        return self.date_range_filter
    
    def clear_date_range_filter(self):
        """清除日期范围过滤器"""
        self.date_range_filter = None
        print("日期范围过滤器已清除")
    
    def apply_date_filter_to_data(self, df, date_column):
        """
        将日期过滤器应用到数据框
        
        Args:
            df: 数据框
            date_column: 日期列名
            
        Returns:
            DataFrame: 过滤后的数据框
        """
        if self.date_range_filter is None or df.empty:
            return df
        
        try:
            # 确保日期列是日期类型
            if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
                df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # 应用日期过滤
            mask = (df[date_column] >= self.date_range_filter['start']) & \
                   (df[date_column] <= self.date_range_filter['end'])
            
            filtered_df = df[mask].copy()
            print(f"日期过滤: 原始数据 {len(df)} 行，过滤后 {len(filtered_df)} 行")
            
            return filtered_df
            
        except Exception as e:
            print(f"应用日期过滤器失败: {e}")
            return df
