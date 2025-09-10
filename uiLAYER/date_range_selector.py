from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QDateEdit, QPushButton, QGroupBox, QFrame, QTextEdit)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import re

class DateRangeSelector(QWidget):
    """
    增强的日期范围选择器组件
    在数据配置完成后自动显示，允许用户选择开始和结束日期
    新增功能：
    1. 显示每个数据源的第一个和最后一个日期
    2. 要求用户选择的日期范围在所有数据的重合范围内
    3. 双线性插值功能
    """
    date_range_changed = pyqtSignal(str, str)  # 开始日期, 结束日期
    interpolation_requested = pyqtSignal(dict)  # 插值请求信号
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.current_date_range = None
        self.data_source_ranges = {}  # 存储各数据源的日期范围
        self.initUI()
        
    def initUI(self):
        """初始化UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建日期范围选择组
        self.create_date_range_group()
        
        # 创建数据源日期范围显示组
        self.create_data_source_ranges_group()
        
        # 创建双线性插值组
        self.create_interpolation_group()
        
        # 初始状态显示，但提示用户配置数据
        self.setVisible(True)
        self.range_info_label.setText("📋 请先在数据配置中选择数据源和列")
        self.range_info_label.setStyleSheet("color: #666666; font-size: 10px; padding: 5px;")
        
    def create_date_range_group(self):
        """创建日期范围选择组"""
        self.date_group = QGroupBox("数据日期范围选择")
        self.date_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout(self.date_group)
        
        # 说明标签
        info_label = QLabel("请选择数据的开始和结束日期，系统将自动对齐所有数据源的时间范围")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 11px;")
        group_layout.addWidget(info_label)
        
        # 日期选择区域
        date_layout = QHBoxLayout()
        
        # 开始日期
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("开始日期:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        start_layout.addWidget(self.start_date_edit)
        date_layout.addLayout(start_layout)
        
        # 结束日期
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("结束日期:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        end_layout.addWidget(self.end_date_edit)
        date_layout.addLayout(end_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("应用日期范围")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.apply_btn.clicked.connect(self.apply_date_range)
        
        self.reset_btn = QPushButton("重置为全部范围")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_to_full_range)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        
        date_layout.addLayout(button_layout)
        group_layout.addLayout(date_layout)
        
        # 当前范围信息
        self.range_info_label = QLabel()
        self.range_info_label.setStyleSheet("color: #666666; font-size: 10px; padding: 5px;")
        self.range_info_label.setWordWrap(True)
        group_layout.addWidget(self.range_info_label)
        
        self.main_layout.addWidget(self.date_group)
    
    def create_data_source_ranges_group(self):
        """创建数据源日期范围显示组"""
        self.ranges_group = QGroupBox("数据源日期范围信息")
        self.ranges_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2196F3;
            }
        """)
        
        group_layout = QVBoxLayout(self.ranges_group)
        
        # 说明标签
        info_label = QLabel("各数据源的日期范围信息（请确保选择的日期范围在所有数据源的重合范围内）")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 11px;")
        group_layout.addWidget(info_label)
        
        # 数据源范围显示区域
        self.ranges_text = QTextEdit()
        self.ranges_text.setMaximumHeight(120)
        self.ranges_text.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        self.ranges_text.setReadOnly(True)
        group_layout.addWidget(self.ranges_text)
        
        self.main_layout.addWidget(self.ranges_group)
    
    def create_interpolation_group(self):
        """创建双线性插值组"""
        self.interpolation_group = QGroupBox("数据插值处理")
        self.interpolation_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF9800;
            }
        """)
        
        group_layout = QVBoxLayout(self.interpolation_group)
        
        # 说明标签
        info_label = QLabel("根据模型的数据步长要求对选中的数据进行双线性插值处理")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 11px;")
        group_layout.addWidget(info_label)
        
        # 插值按钮
        button_layout = QHBoxLayout()
        
        self.interpolate_btn = QPushButton("执行双线性插值")
        self.interpolate_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.interpolate_btn.clicked.connect(self.perform_bilinear_interpolation)
        self.interpolate_btn.setEnabled(False)  # 初始禁用
        
        button_layout.addWidget(self.interpolate_btn)
        button_layout.addStretch()
        
        group_layout.addLayout(button_layout)
        
        # 插值结果信息
        self.interpolation_info_label = QLabel("请先配置数据源并选择日期范围")
        self.interpolation_info_label.setStyleSheet("color: #666666; font-size: 10px; padding: 5px;")
        self.interpolation_info_label.setWordWrap(True)
        group_layout.addWidget(self.interpolation_info_label)
        
        self.main_layout.addWidget(self.interpolation_group)
        
    def update_date_range_from_data(self, reservoir_data_links):
        """
        根据数据配置更新日期范围
        
        Args:
            reservoir_data_links: 水库数据链接字典
        """
        # 如果没有数据链接，显示提示信息
        if not reservoir_data_links:
            self.setVisible(True)
            self.range_info_label.setText("📋 请先在数据配置中选择数据源和列")
            self.range_info_label.setStyleSheet("color: #666666; font-size: 10px; padding: 5px;")
            self.interpolate_btn.setEnabled(False)
            self.interpolation_info_label.setText("请先配置数据源并选择日期范围")
            return
            
        # 获取所有数据源的日期范围
        all_ranges = []
        self.data_source_ranges = {}
        
        print(f"开始获取日期范围，数据链接数量: {len(reservoir_data_links)}")
        
        for link_key, (source_name, col_name) in reservoir_data_links.items():
            try:
                print(f"处理数据链接: {link_key} -> {source_name}.{col_name}")
                date_range = self._get_source_date_range(source_name, col_name)
                if date_range:
                    all_ranges.append(date_range)
                    self.data_source_ranges[link_key] = {
                        'source_name': source_name,
                        'col_name': col_name,
                        'range': date_range
                    }
                    print(f"获取到日期范围: {date_range['start']} 至 {date_range['end']}")
                else:
                    print(f"未获取到日期范围: {source_name}.{col_name}")
            except Exception as e:
                print(f"获取数据源 {source_name} 的日期范围时出错: {e}")
        
        if not all_ranges:
            self.setVisible(False)
            return
            
        # 计算所有数据源的公共日期范围
        min_start = max([r['start'] for r in all_ranges])
        max_end = min([r['end'] for r in all_ranges])
        
        if min_start > max_end:
            # 没有公共范围，显示警告
            self.range_info_label.setText("⚠️ 警告：所选数据源没有公共的日期范围，请检查数据配置")
            self.range_info_label.setStyleSheet("color: #ff6b6b; font-size: 10px; padding: 5px;")
            self.interpolate_btn.setEnabled(False)
        else:
            self.current_date_range = {
                'start': min_start,
                'end': max_end,
                'all_ranges': all_ranges
            }
            
            # 更新日期选择器
            self.start_date_edit.setDate(QDate.fromString(min_start.strftime('%Y-%m-%d'), 'yyyy-MM-dd'))
            self.end_date_edit.setDate(QDate.fromString(max_end.strftime('%Y-%m-%d'), 'yyyy-MM-dd'))
            
            # 更新范围信息
            self._update_range_info()
            
            # 更新数据源范围显示
            self._update_data_source_ranges_display()
            
            # 启用插值按钮
            self.interpolate_btn.setEnabled(True)
            self.interpolation_info_label.setText("✅ 数据配置完成，可以执行双线性插值")
            
            # 显示组件
            self.setVisible(True)
    
    def _get_source_date_range(self, source_name, col_name):
        """
        获取单个数据源的日期范围
        
        Args:
            source_name: 数据源名称
            col_name: 列名
            
        Returns:
            dict: {'start': datetime, 'end': datetime} 或 None
        """
        try:
            if source_name.startswith("[DB] "):
                table_name = source_name.replace("[DB] ", "")
                # 从数据库获取所有列的数据，包括日期列
                query = f'SELECT * FROM "{table_name}" LIMIT 1000'
                print(f"执行SQL查询: {query}")
                df = pd.read_sql_query(query, self.data_manager.db_conn)
                print(f"数据库查询结果: {len(df)} 行")
            else:
                # 从内存数据集获取数据
                if source_name not in self.data_manager.raw_datasets:
                    print(f"数据源 {source_name} 不在内存数据集中")
                    return None
                df = self.data_manager.raw_datasets[source_name].copy()
                print(f"内存数据集查询结果: {len(df)} 行")
            
            if df.empty:
                return None
            
            # 查找日期列（增强版，容忍空格、中文、大小写、非断行空格等）
            original_columns = list(df.columns)
            print(f"数据列: {original_columns}")

            def normalize_col(name: str) -> str:
                if not isinstance(name, str):
                    name = str(name)
                name = name.replace('\xa0', ' ')
                name = name.strip()
                name = re.sub(r"[\s_\-\.（）()]+", "", name)
                return name.lower()

            normalized_to_original = {normalize_col(c): c for c in original_columns}

            date_col = None
            # 优先使用现成日期列
            for key in ['date', 'time', 'datetime', '日期', '时间']:
                if key in normalized_to_original:
                    date_col = normalized_to_original[key]
                    break
            # 退而求其次：寻找包含 date 的列（如 date_new）
            if date_col is None:
                for norm_name, orig_name in normalized_to_original.items():
                    if 'date' in norm_name:
                        date_col = orig_name
                        break

            # 尝试通过 Year/Month/Day 组合
            if date_col is None:
                year_keys = {'year', '年份', '年'}
                month_keys = {'month', '月份', '月'}
                day_keys = {'day', '日期', '日'}

                def find_by_keys(keys):
                    for k in keys:
                        if k in normalized_to_original:
                            return normalized_to_original[k]
                    # 容忍以这些关键字开头或包含（例如有多余的后缀）
                    for norm, orig in normalized_to_original.items():
                        if any(norm == kk or norm.startswith(kk) for kk in keys):
                            return orig
                    return None

                year_col = find_by_keys(year_keys)
                month_col = find_by_keys(month_keys)
                day_col = find_by_keys(day_keys)

                if year_col and month_col and day_col:
                    print(f"找到分开的日期列: {year_col}, {month_col}, {day_col}")
                    try:
                        df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
                        df[month_col] = pd.to_numeric(df[month_col], errors='coerce')
                        df[day_col] = pd.to_numeric(df[day_col], errors='coerce')

                        date_str = (
                            df[year_col].astype('Int64').astype(str) + '-' +
                            df[month_col].astype('Int64').astype(str).str.zfill(2) + '-' +
                            df[day_col].astype('Int64').astype(str).str.zfill(2)
                        )

                        df['date'] = pd.to_datetime(date_str, errors='coerce')
                        date_col = 'date'
                        print("成功合并日期列，创建了 'date' 列")
                    except Exception as e:
                        print(f"合并日期列失败: {e}")
                        date_col = original_columns[0]
                else:
                    print("未找到明确的日期列，尝试将第一列作为日期列")
                    date_col = original_columns[0]
            
            # 尝试将日期列转换为日期类型
            try:
                # 增强解析鲁棒性
                series = df[date_col].astype(str).str.strip()
                series = series.str.replace('\xa0', ' ', regex=False)
                series = series.str.replace('年', '-', regex=False).str.replace('月', '-', regex=False).str.replace('日', '', regex=False)
                series = series.str.replace('/', '-', regex=False).str.replace('.', '-', regex=False)
                # 处理连续8位数字 yyyymmdd
                series = series.str.replace(r'^(\d{4})(\d{2})(\d{2})$', r'\1-\2-\3', regex=True)
                df[date_col] = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
                df = df.dropna(subset=[date_col])
                
                if df.empty:
                    return None
                
                dates = df[date_col]
                
                return {
                    'start': dates.min(),
                    'end': dates.max()
                }
            except Exception as e:
                print(f"转换日期列时出错: {e}")
                return None
            
        except Exception as e:
            print(f"获取数据源 {source_name} 的日期范围时出错: {e}")
            return None
    
    def _update_range_info(self):
        """更新范围信息显示"""
        if not self.current_date_range:
            return
            
        info_text = f"📅 当前选择范围: {self.current_date_range['start'].strftime('%Y-%m-%d')} 至 {self.current_date_range['end'].strftime('%Y-%m-%d')}\n"
        info_text += f"📊 数据源数量: {len(self.current_date_range['all_ranges'])}\n"
        
        # 显示各数据源的范围
        for i, range_info in enumerate(self.current_date_range['all_ranges'][:3]):  # 只显示前3个
            info_text += f"   • 数据源 {i+1}: {range_info['start'].strftime('%Y-%m-%d')} - {range_info['end'].strftime('%Y-%m-%d')}\n"
        
        if len(self.current_date_range['all_ranges']) > 3:
            info_text += f"   • ... 还有 {len(self.current_date_range['all_ranges']) - 3} 个数据源"
        
        self.range_info_label.setText(info_text)
        self.range_info_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 5px;")
    
    def _update_data_source_ranges_display(self):
        """更新数据源范围显示"""
        if not self.data_source_ranges:
            self.ranges_text.setPlainText("暂无数据源信息")
            return
        
        display_text = "数据源日期范围详情:\n"
        display_text += "=" * 50 + "\n"
        
        for link_key, info in self.data_source_ranges.items():
            source_name = info['source_name']
            col_name = info['col_name']
            date_range = info['range']
            
            # 简化显示名称
            if source_name.startswith("[DB] "):
                display_name = source_name.replace("[DB] ", "")
            else:
                display_name = source_name
            
            display_text += f"📊 {display_name}.{col_name}\n"
            display_text += f"   第一个日期: {date_range['start'].strftime('%Y-%m-%d')}\n"
            display_text += f"   最后一个日期: {date_range['end'].strftime('%Y-%m-%d')}\n"
            display_text += f"   数据天数: {(date_range['end'] - date_range['start']).days + 1}\n"
            display_text += "-" * 30 + "\n"
        
        # 显示公共范围
        if self.current_date_range:
            display_text += f"\n🎯 公共日期范围:\n"
            display_text += f"   开始: {self.current_date_range['start'].strftime('%Y-%m-%d')}\n"
            display_text += f"   结束: {self.current_date_range['end'].strftime('%Y-%m-%d')}\n"
            display_text += f"   可用天数: {(self.current_date_range['end'] - self.current_date_range['start']).days + 1}\n"
        
        self.ranges_text.setPlainText(display_text)
    
    def apply_date_range(self):
        """应用选择的日期范围"""
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        
        if start_date > end_date:
            self.range_info_label.setText("❌ 错误：开始日期不能晚于结束日期")
            self.range_info_label.setStyleSheet("color: #ff6b6b; font-size: 10px; padding: 5px;")
            return
        
        # 检查选择的日期是否在所有数据源范围内
        if self.current_date_range:
            if start_date < self.current_date_range['start'].date() or end_date > self.current_date_range['end'].date():
                self.range_info_label.setText("⚠️ 警告：选择的日期范围超出部分数据源的范围，可能导致数据缺失")
                self.range_info_label.setStyleSheet("color: #ffa726; font-size: 10px; padding: 5px;")
            else:
                self.range_info_label.setText("✅ 日期范围选择正确，在所有数据源范围内")
                self.range_info_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 5px;")
        
        # 发送日期范围变化信号
        self.date_range_changed.emit(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # 更新插值按钮状态
        self.interpolate_btn.setEnabled(True)
        self.interpolation_info_label.setText("✅ 日期范围已应用，可以执行双线性插值")
    
    def reset_to_full_range(self):
        """重置为全部可用范围"""
        if self.current_date_range:
            self.start_date_edit.setDate(QDate.fromString(
                self.current_date_range['start'].strftime('%Y-%m-%d'), 'yyyy-MM-dd'))
            self.end_date_edit.setDate(QDate.fromString(
                self.current_date_range['end'].strftime('%Y-%m-%d'), 'yyyy-MM-dd'))
            
            self._update_range_info()
            
            # 发送重置信号
            self.date_range_changed.emit(
                self.current_date_range['start'].strftime('%Y-%m-%d'),
                self.current_date_range['end'].strftime('%Y-%m-%d')
            )
            
            # 更新插值按钮状态
            self.interpolate_btn.setEnabled(True)
            self.interpolation_info_label.setText("✅ 已重置为全部范围，可以执行双线性插值")
    
    def perform_bilinear_interpolation(self):
        """执行双线性插值"""
        try:
            # 获取当前选择的日期范围
            start_date = self.start_date_edit.date().toPyDate()
            end_date = self.end_date_edit.date().toPyDate()
            
            if start_date > end_date:
                self.interpolation_info_label.setText("❌ 错误：开始日期不能晚于结束日期")
                return
            
            # 获取所有数据链接
            all_links = getattr(self.data_manager, 'multi_reservoir_data_links', {})
            
            if not all_links:
                self.interpolation_info_label.setText("❌ 错误：没有配置数据链接，请先在数据配置中设置数据源")
                print("数据链接为空，请检查数据配置")
                return
            
            print(f"开始插值，数据链接数量: {len(all_links)}")
            print(f"数据链接: {all_links}")
            
            # 执行插值
            interpolation_results = self._perform_bilinear_interpolation_on_data(
                all_links, start_date, end_date
            )
            
            if interpolation_results:
                # 发送插值请求信号
                self.interpolation_requested.emit(interpolation_results)
                
                self.interpolation_info_label.setText("✅ 双线性插值完成，数据已更新")
                self.interpolation_info_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 5px;")
                
                print(f"双线性插值完成，处理了 {len(interpolation_results)} 个数据源")
            else:
                self.interpolation_info_label.setText("❌ 插值失败，请检查数据")
                print("插值返回None，可能是数据问题")
                
        except Exception as e:
            print(f"执行双线性插值时出错: {e}")
            import traceback
            traceback.print_exc()
            self.interpolation_info_label.setText(f"❌ 插值出错: {str(e)}")
    
    def _perform_bilinear_interpolation_on_data(self, data_links, start_date, end_date):
        """
        对数据进行线性插值，自动屏蔽0数据
        
        Args:
            data_links: 数据链接字典
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 插值结果
        """
        try:
            # 检查scipy是否可用
            try:
                from scipy.interpolate import interp1d
            except ImportError:
                print("错误：需要安装scipy库进行插值")
                return None
            
            interpolation_results = {}
            
            # 生成目标日期序列（按天）
            target_dates = pd.date_range(start=start_date, end=end_date, freq='D')
            print(f"目标日期范围: {len(target_dates)} 天")
            
            for link_key, (source_name, col_name) in data_links.items():
                try:
                    print(f"处理数据链接: {link_key} -> {source_name}.{col_name}")
                    
                    # 检查是否为日期列
                    if col_name.lower() in ['date', 'time', 'datetime']:
                        print(f"跳过日期列: {col_name}")
                        continue
                    
                    # 获取原始数据（包括日期列）
                    if source_name.startswith("[DB] "):
                        table_name = source_name.replace("[DB] ", "")
                        # 获取所有列以找到日期列
                        query = f'SELECT * FROM "{table_name}" LIMIT 1000'
                        df = pd.read_sql_query(query, self.data_manager.db_conn)
                        print(f"从数据库获取数据: {len(df)} 行")
                    else:
                        if source_name not in self.data_manager.raw_datasets:
                            print(f"数据源 {source_name} 不在内存数据集中")
                            continue
                        df = self.data_manager.raw_datasets[source_name].copy()
                        print(f"从内存获取数据: {len(df)} 行")
                    
                    if df.empty:
                        print(f"数据为空: {source_name}")
                        continue
                    
                    # 查找日期列（增强版，容忍空格、中文、大小写、非断行空格等）
                    original_columns = list(df.columns)
                    print(f"数据列: {original_columns}")

                    def normalize_col(name: str) -> str:
                        if not isinstance(name, str):
                            name = str(name)
                        name = name.replace('\xa0', ' ')
                        name = name.strip()
                        name = re.sub(r"[\s_\-\.（）()]+", "", name)
                        return name.lower()

                    normalized_to_original = {normalize_col(c): c for c in original_columns}

                    date_col = None
                    for key in ['date', 'time', 'datetime', '日期', '时间']:
                        if key in normalized_to_original:
                            date_col = normalized_to_original[key]
                            break
                    if date_col is None:
                        for norm_name, orig_name in normalized_to_original.items():
                            if 'date' in norm_name:
                                date_col = orig_name
                                break

                    if date_col is None:
                        year_keys = {'year', '年份', '年'}
                        month_keys = {'month', '月份', '月'}
                        day_keys = {'day', '日期', '日'}

                        def find_by_keys(keys):
                            for k in keys:
                                if k in normalized_to_original:
                                    return normalized_to_original[k]
                            for norm, orig in normalized_to_original.items():
                                if any(norm == kk or norm.startswith(kk) for kk in keys):
                                    return orig
                            return None

                        year_col = find_by_keys(year_keys)
                        month_col = find_by_keys(month_keys)
                        day_col = find_by_keys(day_keys)

                        if year_col and month_col and day_col:
                            print(f"找到分开的日期列: {year_col}, {month_col}, {day_col}")
                            try:
                                df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
                                df[month_col] = pd.to_numeric(df[month_col], errors='coerce')
                                df[day_col] = pd.to_numeric(df[day_col], errors='coerce')

                                date_str = (
                                    df[year_col].astype('Int64').astype(str) + '-' +
                                    df[month_col].astype('Int64').astype(str).str.zfill(2) + '-' +
                                    df[day_col].astype('Int64').astype(str).str.zfill(2)
                                )

                                df['date'] = pd.to_datetime(date_str, errors='coerce')
                                date_col = 'date'
                                print("成功合并日期列，创建了 'date' 列")
                            except Exception as e:
                                print(f"合并日期列失败: {e}")
                                date_col = original_columns[0]
                        else:
                            print(f"未找到日期列，使用第一列: {original_columns[0]}")
                            date_col = original_columns[0]
                    
                    # 确保日期列是日期类型（鲁棒解析）
                    series = df[date_col].astype(str).str.strip()
                    series = series.str.replace('\xa0', ' ', regex=False)
                    series = series.str.replace('年', '-', regex=False).str.replace('月', '-', regex=False).str.replace('日', '', regex=False)
                    series = series.str.replace('/', '-', regex=False).str.replace('.', '-', regex=False)
                    series = series.str.replace(r'^(\d{4})(\d{2})(\d{2})$', r'\1-\2-\3', regex=True)
                    df[date_col] = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
                    df = df.dropna(subset=[date_col])
                    
                    if df.empty:
                        print(f"转换日期后数据为空: {source_name}")
                        continue
                    
                    # 检查目标列是否存在
                    if col_name not in df.columns:
                        print(f"目标列 {col_name} 不存在于数据中")
                        continue
                    
                    # 过滤日期范围
                    mask = (df[date_col] >= pd.Timestamp(start_date)) & \
                           (df[date_col] <= pd.Timestamp(end_date))
                    df_filtered = df[mask].copy()
                    
                    if df_filtered.empty:
                        print(f"过滤后数据为空: {source_name}")
                        continue
                    
                    print(f"过滤后数据: {len(df_filtered)} 行")
                    
                    # 对数值列进行线性插值
                    if pd.api.types.is_numeric_dtype(df_filtered[col_name]):
                        # 准备插值数据
                        x_original = (df_filtered[date_col] - pd.Timestamp(start_date)).dt.total_seconds()
                        y_original = df_filtered[col_name].values
                        
                        # 检查数据有效性
                        if len(x_original) < 2:
                            print(f"数据点不足，无法插值: {len(x_original)} 个点")
                            continue
                        
                        # 自动屏蔽0数据和NaN数据
                        print(f"原始数据统计: 总数={len(y_original)}, 0值={np.sum(y_original == 0)}, NaN值={np.sum(np.isnan(y_original))}")
                        
                        # 创建有效数据掩码（排除0值和NaN值）
                        valid_mask = (y_original != 0) & ~np.isnan(y_original)
                        
                        if np.sum(valid_mask) < 2:
                            print(f"有效数据点不足（排除0值和NaN后）: {np.sum(valid_mask)} 个点")
                            # 如果有效数据太少，尝试只排除NaN值
                            valid_mask = ~np.isnan(y_original)
                            if np.sum(valid_mask) < 2:
                                print(f"即使只排除NaN，数据点仍不足: {np.sum(valid_mask)} 个点")
                                continue
                            else:
                                print(f"使用只排除NaN的策略，有效数据点: {np.sum(valid_mask)} 个")
                        
                        # 应用有效数据掩码
                        x_valid = x_original[valid_mask]
                        y_valid = y_original[valid_mask]
                        
                        print(f"屏蔽0数据后: 有效数据点={len(x_valid)}, 屏蔽的数据点={len(x_original) - len(x_valid)}")
                        
                        try:
                            # 创建插值函数（使用有效数据）
                            f = interp1d(x_valid, y_valid, kind='linear', 
                                        bounds_error=False, fill_value=y_valid[0])
                            
                            # 计算目标时间点
                            x_target = (target_dates - pd.Timestamp(start_date)).total_seconds()
                            
                            # 执行插值
                            y_interpolated = f(x_target)
                            
                            # 处理可能的NaN值（插值结果中的NaN）
                            if np.any(np.isnan(y_interpolated)):
                                print(f"插值结果包含NaN值，进行填充处理")
                                # 使用简单的填充方法
                                valid_mean = np.nanmean(y_valid)
                                y_interpolated = np.where(np.isnan(y_interpolated), valid_mean, y_interpolated)
                            
                            # 创建插值结果DataFrame
                            interpolated_df = pd.DataFrame({
                                'date': target_dates,
                                col_name: y_interpolated
                            })
                            
                            # 添加插值统计信息
                            interpolation_stats = {
                                'original_total_points': len(x_original),
                                'original_zero_points': np.sum(y_original == 0),
                                'original_nan_points': np.sum(np.isnan(y_original)),
                                'valid_points_used': len(x_valid),
                                'interpolated_points': len(y_interpolated),
                                'zero_data_masked': True,
                                'interpolation_method': 'linear_with_zero_masking'
                            }
                            
                            interpolation_results[link_key] = {
                                'source_name': source_name,
                                'col_name': col_name,
                                'original_data': df_filtered,
                                'interpolated_data': interpolated_df,
                                'interpolation_stats': interpolation_stats,
                                'interpolation_method': 'linear_with_zero_masking'
                            }
                            
                            print(f"✅ 完成 {link_key} 的插值（已屏蔽0数据）")
                            print(f"  原始数据: {len(df_filtered)} 行")
                            print(f"  有效数据点: {len(x_valid)} 个")
                            print(f"  插值后: {len(interpolated_df)} 行")
                            print(f"  屏蔽的0值数据点: {np.sum(y_original == 0)} 个")
                            
                        except Exception as e:
                            print(f"插值计算失败: {e}")
                            continue
                    else:
                        print(f"列 {col_name} 不是数值类型，跳过插值")
                
                except Exception as e:
                    print(f"处理 {link_key} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            return interpolation_results
            
        except Exception as e:
            print(f"插值过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_current_date_range(self):
        """获取当前选择的日期范围"""
        if not self.current_date_range:
            return None
            
        return {
            'start': self.start_date_edit.date().toPyDate(),
            'end': self.end_date_edit.date().toPyDate()
        }
