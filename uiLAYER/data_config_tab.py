from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QHBoxLayout, 
                             QComboBox, QPushButton, QFrame, QScrollArea, QGroupBox, QSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSlot, pyqtSignal
from functools import partial
from .ui_utils import TRANSLATIONS, MODEL_DATA_REQUIREMENTS
from .date_range_selector import DateRangeSelector

class DataConfigTab(QWidget):
    """
    '数据配置'选项卡的UI界面。
    UI根据所选模型动态更新，允许用户将模型需求链接到数据池中的具体数据列。
    支持多水库配置。
    """
    link_changed = pyqtSignal()

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.reservoir_widgets = {}  # 存储每个水库的配置widget
        self.reservoir_count = 1  # 当前水库数量
        self.current_model = None
        self.initUI()

    def load_example_data(self, model_name):
        """从数据库中的示例水库加载示例数据到数据库并自动建立数据链接"""
        try:
            import os
            import pandas as pd
            
            # 构建示例水库中的数据文件路径
            if model_name == "SCS-CN":
                example_file_name = "SCS-CN示例数据.csv"
            elif model_name == "Saint-Venant":
                example_file_name = "Saint-Venant示例数据.csv"
            else:
                return False, f"未找到 {model_name} 模型的示例数据"
            
            # 构建完整路径
            if model_name == "SCS-CN":
                example_file_name = "scs_cn_example_data.csv"
            elif model_name == "Saint-Venant":
                example_file_name = "saint_venant_example_data.csv"
            
            full_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'example_data', 
                example_file_name
            )
            
            if not os.path.exists(full_path):
                return False, f"示例数据文件不存在: {full_path}"
            
            # 将示例数据导入到数据库中
            table_name = self.data_manager.import_file_to_db(full_path, table_prefix="示例")
            if table_name is None:
                return False, "导入示例数据到数据库失败"
            
            # 自动建立数据链接
            self._auto_setup_data_links(model_name, table_name)
            
            # 读取数据以获取记录数
            df = pd.read_csv(full_path)
            df['date'] = pd.to_datetime(df['date'])
            
            return True, f"成功将 {model_name} 模型示例数据导入到数据库表 '{table_name}'，共 {len(df)} 条记录，并自动建立了数据链接"
            
        except Exception as e:
            return False, f"加载示例数据时发生错误: {str(e)}"
    
    def _auto_setup_data_links(self, model_name, table_name):
        """自动为示例数据建立数据链接"""
        try:
            # 获取模型所需的数据类型
            required_data_types = MODEL_DATA_REQUIREMENTS.get(model_name, [])
            
            # 获取数据库表的列信息
            cursor = self.data_manager.db_conn.cursor()
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # 定义列名映射（示例数据列名 -> 模型数据类型）
            column_mapping = {
                # SCS-CN模型映射
                "rainfall": "precipitation",
                "temperature": "temperature", 
                "evaporation": "evaporation",
                # "antecedent_rainfall": "antecedent_rainfall",  # 已移除：现在由系统自动计算
                
                # Saint-Venant模型映射
                "upstream_discharge": "upstream_discharge",
                "downstream_depth": "downstream_depth",
                "wind_speed": "wind_speed",
                "wind_direction": "wind_direction",
                "water_temperature": "water_temperature"
            }
            
            # 为每个水库建立数据链接
            for reservoir_id in range(1, self.reservoir_count + 1):
                for col_name in column_names:
                    if col_name in column_mapping:
                        data_type = column_mapping[col_name]
                        if data_type in required_data_types:
                            link_key = f"{reservoir_id}_{data_type}"
                            source_name = f"[DB] {table_name}"
                            
                            # 建立数据链接
                            self.data_manager.set_multi_reservoir_data_link(
                                reservoir_id, data_type, source_name, col_name
                            )
                            print(f"自动建立数据链接: {link_key} -> {source_name}.{col_name}")
            
            print(f"为 {model_name} 模型自动建立了数据链接")
            
        except Exception as e:
            print(f"自动建立数据链接时出错: {e}")

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        
        # 创建水库数量控制区域
        self.create_reservoir_control_area()
        
        # 创建滚动区域来显示多个水库的配置
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)
        
        # 添加日期范围选择器
        self.date_range_selector = DateRangeSelector(self.data_manager)
        self.date_range_selector.date_range_changed.connect(self.on_date_range_changed)
        self.date_range_selector.interpolation_requested.connect(self.on_interpolation_requested)
        self.main_layout.addWidget(self.date_range_selector)
        
        self.info_label = QLabel("请先在'模型配置'选项卡中选择一个模型。")
        self.scroll_layout.addWidget(self.info_label)

    def create_reservoir_control_area(self):
        """创建水库数量控制区域"""
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        
        control_layout.addWidget(QLabel("水库数量:"))
        
        self.reservoir_count_spinbox = QSpinBox()
        self.reservoir_count_spinbox.setMinimum(1)
        self.reservoir_count_spinbox.setMaximum(10)
        self.reservoir_count_spinbox.setValue(1)
        self.reservoir_count_spinbox.valueChanged.connect(self.on_reservoir_count_changed)
        control_layout.addWidget(self.reservoir_count_spinbox)
        
        self.add_reservoir_btn = QPushButton("增加水库")
        self.add_reservoir_btn.clicked.connect(self.add_reservoir)
        control_layout.addWidget(self.add_reservoir_btn)
        
        self.remove_reservoir_btn = QPushButton("删减水库")
        self.remove_reservoir_btn.clicked.connect(self.remove_reservoir)
        control_layout.addWidget(self.remove_reservoir_btn)
        
        # 添加示例数据按钮
        self.example_data_btn = QPushButton("加载示例数据")
        self.example_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A6FE2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2B57C1;
            }
            QPushButton:pressed {
                background-color: #1E3F88;
            }
            QPushButton:disabled {
                background-color: #E5E7EB;
                color: #9CA3AF;
            }
        """)
        self.example_data_btn.clicked.connect(self.on_load_example_data)
        self.example_data_btn.setEnabled(False)  # 初始禁用
        control_layout.addWidget(self.example_data_btn)
        
        control_layout.addStretch()
        self.main_layout.addWidget(control_frame)

    @pyqtSlot(str)
    def update_ui_for_model(self, model_name):
        """根据选择的模型名称，动态更新UI。"""
        self.current_model = model_name
        self.clear_all_reservoir_widgets()

        if not model_name or model_name not in MODEL_DATA_REQUIREMENTS:
            self.info_label = QLabel("请先在'模型配置'选项卡中选择一个模型。")
            self.scroll_layout.addWidget(self.info_label)
            # 禁用示例数据按钮
            self.example_data_btn.setEnabled(False)
            return

        # 启用示例数据按钮
        self.example_data_btn.setEnabled(True)

        # 为当前水库数量创建配置界面
        for i in range(self.reservoir_count):
            self.create_reservoir_config_widget(i + 1)

    def clear_all_reservoir_widgets(self):
        """清理所有水库配置widget"""
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.reservoir_widgets.clear()

    def create_reservoir_config_widget(self, reservoir_id):
        """为指定水库ID创建配置widget"""
        if not self.current_model or self.current_model not in MODEL_DATA_REQUIREMENTS:
            return

        # 创建水库分组框
        group_box = QGroupBox(f"水库 {reservoir_id}")
        group_layout = QFormLayout(group_box)
        
        requirements = MODEL_DATA_REQUIREMENTS[self.current_model]
        reservoir_widgets = {}
        
        for req_id in requirements:
            display_name = TRANSLATIONS.get(req_id, req_id)
            label = QLabel(f"{display_name}:")

            file_combo = QComboBox()
            col_combo = QComboBox()
            
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel("文件:"))
            row_layout.addWidget(file_combo)
            row_layout.addWidget(QLabel("列:"))
            row_layout.addWidget(col_combo)

            group_layout.addRow(label, row_layout)
            reservoir_widgets[req_id] = {'file_combo': file_combo, 'col_combo': col_combo}

            # 绑定信号，传递水库ID
            file_combo.currentTextChanged.connect(
                partial(self.on_file_combo_changed, reservoir_id, req_id, file_combo, col_combo))
            col_combo.currentTextChanged.connect(
                partial(self.on_col_combo_changed, reservoir_id, req_id, file_combo, col_combo))

        self.reservoir_widgets[reservoir_id] = reservoir_widgets
        self.scroll_layout.addWidget(group_box)
        
        # 添加分隔线（除了最后一个水库）
        if reservoir_id < self.reservoir_count:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            self.scroll_layout.addWidget(separator)

        # 填充文件下拉框
        self.populate_reservoir_file_combos(reservoir_id)

    def on_reservoir_count_changed(self, value):
        """水库数量变化时的处理"""
        self.reservoir_count = value
        self.update_reservoir_buttons_state()
        if self.current_model:
            self.update_ui_for_model(self.current_model)

    def add_reservoir(self):
        """增加一个水库"""
        if self.reservoir_count < 10:
            self.reservoir_count += 1
            self.reservoir_count_spinbox.setValue(self.reservoir_count)
            self.update_reservoir_buttons_state()
            if self.current_model:
                self.update_ui_for_model(self.current_model)

    def remove_reservoir(self):
        """删减一个水库"""
        if self.reservoir_count > 1:
            self.reservoir_count -= 1
            self.reservoir_count_spinbox.setValue(self.reservoir_count)
            self.update_reservoir_buttons_state()
            if self.current_model:
                self.update_ui_for_model(self.current_model)

    def update_reservoir_buttons_state(self):
        """更新增加/删减按钮的状态"""
        self.add_reservoir_btn.setEnabled(self.reservoir_count < 10)
        self.remove_reservoir_btn.setEnabled(self.reservoir_count > 1)

    def populate_reservoir_file_combos(self, reservoir_id):
        """为指定水库填充文件下拉框"""
        if reservoir_id not in self.reservoir_widgets:
            return
            
        source_names = [""] + self.data_manager.get_all_data_source_names()
        for req_id, widget_set in self.reservoir_widgets[reservoir_id].items():
            widget_set['file_combo'].blockSignals(True)
            widget_set['file_combo'].clear()
            widget_set['file_combo'].addItems(source_names)
            
            # 设置文件级工具提示
            for idx in range(1, widget_set['file_combo'].count()):
                src_name = widget_set['file_combo'].itemText(idx)
                tooltip = self._generate_file_tooltip(src_name)
                widget_set['file_combo'].setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)
            widget_set['file_combo'].blockSignals(False)
            
            # 尝试恢复之前的选择
            link_key = f"{reservoir_id}_{req_id}"
            if hasattr(self.data_manager, 'multi_reservoir_data_links') and link_key in self.data_manager.multi_reservoir_data_links:
                saved_source, saved_col = self.data_manager.multi_reservoir_data_links[link_key]
                if saved_source in source_names:
                    widget_set['file_combo'].setCurrentText(saved_source)
                    self.on_file_combo_changed(reservoir_id, req_id, widget_set['file_combo'], widget_set['col_combo'], saved_source)
                    if saved_col in [widget_set['col_combo'].itemText(i) for i in range(widget_set['col_combo'].count())]:
                        widget_set['col_combo'].setCurrentText(saved_col)

    def _generate_file_tooltip(self, source_name):
        """生成文件级数据预览工具提示文本。"""
        preview_text = "预览不可用"
        try:
            if source_name.startswith("[DB] "):
                table_name = source_name.replace("[DB] ", "")
                preview_df = self.data_manager.db_conn.execute(f'SELECT * FROM "{table_name}" LIMIT 5').fetchall()
                if preview_df:
                    # Convert to string
                    import pandas as pd
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

    def _generate_column_tooltip(self, source_name, col_name):
        """生成某列数据预览文本。"""
        preview_text = "预览不可用"
        try:
            if source_name.startswith("[DB] "):
                table_name = source_name.replace("[DB] ", "")
                query = f'SELECT "{col_name}" FROM "{table_name}" LIMIT 5'
                import pandas as pd
                df = pd.read_sql_query(query, self.data_manager.db_conn)
                preview_text = df.to_string(index=False, max_colwidth=20)
            else:
                df_full = self.data_manager.raw_datasets.get(source_name)
                if df_full is not None and col_name in df_full.columns:
                    preview_text = df_full[[col_name]].head(5).to_string(index=False, max_colwidth=20)
        except Exception as e:
            preview_text = f"预览失败: {e}"
        return preview_text

    def on_file_combo_changed(self, reservoir_id, req_id, file_combo, col_combo, filename):
        """当文件下拉框变化时，更新对应的列下拉框。"""
        col_combo.blockSignals(True)
        col_combo.clear()
        if filename:
            columns = [""] + self.data_manager.get_source_columns(filename)
            col_combo.addItems(columns)
            # 为列下拉框设置预览
            for idx in range(1, col_combo.count()):
                col_name_item = col_combo.itemText(idx)
                tooltip = self._generate_column_tooltip(filename, col_name_item)
                col_combo.setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)
        col_combo.blockSignals(False)
        self.on_col_combo_changed(reservoir_id, req_id, file_combo, col_combo, col_combo.currentText())

    def on_col_combo_changed(self, reservoir_id, req_id, file_combo, col_combo, col_name):
        """当列下拉框变化时，设置数据链接。"""
        filename = file_combo.currentText()
        link_key = f"{reservoir_id}_{req_id}"
        
        # 确保数据管理器有多水库数据链接字典
        if not hasattr(self.data_manager, 'multi_reservoir_data_links'):
            self.data_manager.multi_reservoir_data_links = {}
        
        if filename and col_name:
            self.data_manager.multi_reservoir_data_links[link_key] = (filename, col_name)
        else:
            # 如果选择为空，则清除该链接
            if link_key in self.data_manager.multi_reservoir_data_links:
                del self.data_manager.multi_reservoir_data_links[link_key]
        
        # 自动更新日期范围选择器
        self.update_date_range_selector()
        
        self.link_changed.emit()

    def refresh_data_sources(self):
        """公共方法，用于在数据池更新时刷新文件下拉框。"""
        for reservoir_id in self.reservoir_widgets.keys():
            self.populate_reservoir_file_combos(reservoir_id)
        
        # 刷新数据源后，更新日期范围选择器
        self.update_date_range_selector()
    
    def get_all_reservoir_data_links(self):
        """获取所有水库的数据链接"""
        if not hasattr(self.data_manager, 'multi_reservoir_data_links'):
            return {}
        return self.data_manager.multi_reservoir_data_links
    
    def on_date_range_changed(self, start_date, end_date):
        """当日期范围变化时的处理"""
        print(f"日期范围已更新: {start_date} 至 {end_date}")
        # 设置数据管理器的日期范围过滤器
        self.data_manager.set_date_range_filter(start_date, end_date)
    
    def on_interpolation_requested(self, interpolation_results):
        """当插值请求时的处理"""
        print(f"收到插值请求，处理 {len(interpolation_results)} 个数据源")
        
        # 将插值结果存储到数据管理器
        if hasattr(self.data_manager, 'interpolated_data'):
            self.data_manager.interpolated_data.update(interpolation_results)
        else:
            self.data_manager.interpolated_data = interpolation_results
        
        print("插值数据已存储到数据管理器")
    
    def update_date_range_selector(self):
        """更新日期范围选择器"""
        # 获取所有水库的数据链接
        all_links = self.get_all_reservoir_data_links()
        
        # 检查是否有完整的数据配置
        if all_links:
            # 更新日期范围选择器
            self.date_range_selector.update_date_range_from_data(all_links)

    def on_load_example_data(self):
        """加载示例数据按钮点击事件"""
        if not self.current_model:
            return
            
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, 
            "确认加载示例数据", 
            f"确定要加载 {self.current_model} 模型的示例数据吗？\n\n这将添加示例数据到数据池中。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.load_example_data(self.current_model)
            
            if success:
                QMessageBox.information(self, "成功", message)
                # 刷新数据源
                self.refresh_data_sources()
                # 发出链接变化信号
                self.link_changed.emit()
            else:
                QMessageBox.warning(self, "警告", message)
