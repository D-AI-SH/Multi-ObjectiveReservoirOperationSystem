from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                             QGroupBox, QScrollArea, QComboBox, QLabel, 
                             QPushButton, QTabWidget, QFrame, QSplitter, 
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TABLEAU_COLORS, CSS4_COLORS
import pandas as pd
import os

# 设置全局中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class MplCanvas(FigureCanvas):
    """一个嵌入了matplotlib图像的QWidget。"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class VisTab(QWidget):
    """
    '可视化结果'选项卡的UI界面。
    为每个字段创建独立的时间序列图，支持垂直滚动查看。
    """
    def __init__(self):
        super().__init__()
        self.data_storage = {
            'input_data': {},      # 输入数据: {reservoir_id: DataFrame}
            'model_results': {},   # 模型结果: {reservoir_id: DataFrame}
            'schedule_results': {} # 调度结果: {result_type: DataFrame}
        }
        self.color_mapping = {}  # 水库ID到颜色的映射
        self.field_charts = {}   # 字段图表映射: {field_name: canvas}
        self.init_colors()
        self.initUI()

    def init_colors(self):
        """初始化颜色映射"""
        colors = list(TABLEAU_COLORS.keys()) + list(CSS4_COLORS.keys())[:20]
        for i in range(1, 11):  # 支持最多10个水库
            self.color_mapping[i] = colors[i % len(colors)]

    def initUI(self):
        main_layout = QHBoxLayout(self)
        
        # 使用QSplitter创建可调整的分割布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 右侧图表区域
        chart_area = self.create_chart_area()
        splitter.addWidget(chart_area)
        
        # 设置分割比例：控制面板20%，图表区域80%
        splitter.setSizes([300, 1200])
        
        main_layout.addWidget(splitter)

    def create_control_panel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)
        
        # 数据类型选择
        data_type_group = QGroupBox("数据类型")
        data_type_layout = QVBoxLayout(data_type_group)
        
        self.input_data_cb = QCheckBox("输入数据")
        self.model_results_cb = QCheckBox("模型结果")
        self.schedule_results_cb = QCheckBox("调度优化结果")
        
        # 连接信号
        self.input_data_cb.toggled.connect(self.on_data_type_changed)
        self.model_results_cb.toggled.connect(self.on_data_type_changed)
        self.schedule_results_cb.toggled.connect(self.on_data_type_changed)
        
        data_type_layout.addWidget(self.input_data_cb)
        data_type_layout.addWidget(self.model_results_cb)
        data_type_layout.addWidget(self.schedule_results_cb)
        
        layout.addWidget(data_type_group)
        
        # 水库选择区域
        reservoir_group = QGroupBox("水库选择")
        reservoir_layout = QVBoxLayout(reservoir_group)
        
        # 全选/全不选按钮
        select_buttons_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.deselect_all_btn = QPushButton("全不选")
        select_buttons_layout.addWidget(self.select_all_btn)
        select_buttons_layout.addWidget(self.deselect_all_btn)
        reservoir_layout.addLayout(select_buttons_layout)
        
        # 水库复选框区域（使用滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(150)
        
        scroll_widget = QWidget()
        self.reservoir_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        reservoir_layout.addWidget(scroll_area)
        
        layout.addWidget(reservoir_group)
        
        # 字段选择区域
        field_group = QGroupBox("字段选择")
        field_layout = QVBoxLayout(field_group)
        
        # 字段复选框区域（使用滚动区域）
        field_scroll_area = QScrollArea()
        field_scroll_area.setWidgetResizable(True)
        field_scroll_area.setMaximumHeight(200)
        
        field_scroll_widget = QWidget()
        self.field_layout = QVBoxLayout(field_scroll_widget)
        field_scroll_area.setWidget(field_scroll_widget)
        field_layout.addWidget(field_scroll_area)
        
        layout.addWidget(field_group)
        
        # 连接按钮信号
        self.select_all_btn.clicked.connect(self.select_all_reservoirs)
        self.deselect_all_btn.clicked.connect(self.deselect_all_reservoirs)
        
        layout.addStretch()
        return panel

    def create_chart_area(self):
        """创建右侧图表区域 - 为每个字段创建独立的时间序列图"""
        # 主容器
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 滚动内容容器
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        
        # 初始时显示提示信息
        self.show_empty_message()
        
        # 设置滚动区域内容
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        # 添加保存按钮
        button_layout = QHBoxLayout()
        self.save_all_btn = QPushButton("保存所有图表")
        self.save_all_btn.clicked.connect(self.save_all_charts)
        button_layout.addWidget(self.save_all_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        return main_widget
    
    def show_empty_message(self):
        """显示空状态提示信息"""
        self.clear_all_charts()
        
        empty_label = QLabel("请选择数据类型、水库和字段以显示图表")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("font-size: 16px; color: #6B7280; margin: 50px;")
        # 设置中文字体
        font = QFont("Microsoft YaHei", 14)
        empty_label.setFont(font)
        self.scroll_layout.addWidget(empty_label)
    
    def clear_all_charts(self):
        """清除所有图表"""
        # 清除布局中的所有控件
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child is not None:
                widget = child.widget()
                if widget is not None:
                    widget.deleteLater()
        
        # 清空字段图表字典
        self.field_charts.clear()
    
    def create_field_chart(self, field_name):
        """为指定字段创建独立的时间序列图"""
        # 创建图表框架
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("QFrame { border: 1px solid #DEE2E6; margin: 5px; padding: 10px; background: #FFFFFF; }")
        
        layout = QVBoxLayout(frame)
        
        # 添加标题
        title_label = QLabel(f"字段：{field_name}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #374151; margin: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 设置中文字体
        font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        title_label.setFont(font)
        layout.addWidget(title_label)

        # 工具栏：单图保存
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        save_btn = QPushButton("保存图片")
        toolbar.addWidget(save_btn)
        layout.addLayout(toolbar)

        # 创建图表画布 - 初始较大，清晰显示
        canvas = MplCanvas(self, width=12, height=7, dpi=100)
        layout.addWidget(canvas)

        def on_save():
            try:
                safe_field_name = "".join(c for c in field_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                default_name = f"字段_{safe_field_name}_时间序列图.png"
                file_path, _ = QFileDialog.getSaveFileName(self, "保存图像", default_name, "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg);;PDF 文件 (*.pdf)")
                if not file_path:
                    return
                canvas.figure.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
                QMessageBox.information(self, "保存成功", f"已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存图像时发生错误:\n{str(e)}")

        save_btn.clicked.connect(on_save)
        
        # 设置框架最小高度，避免图表被压缩
        frame.setMinimumHeight(500)
        
        # 添加到滚动布局
        self.scroll_layout.addWidget(frame)
        
        # 存储到字典
        self.field_charts[field_name] = canvas
        
        return canvas

    def on_data_type_changed(self):
        """数据类型选择变化时更新UI"""
        self.update_reservoir_checkboxes()
        self.update_field_checkboxes()
        self.update_plot()  # 更新图表显示

    def update_reservoir_checkboxes(self):
        """更新水库复选框"""
        # 清理现有复选框
        while self.reservoir_layout.count():
            item = self.reservoir_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # 根据选择的数据类型显示相应的水库
        available_reservoirs = set()
        
        if self.input_data_cb.isChecked():
            available_reservoirs.update(self.data_storage['input_data'].keys())
        if self.model_results_cb.isChecked():
            available_reservoirs.update(self.data_storage['model_results'].keys())
        
        # 为每个可用水库创建复选框
        for reservoir_id in sorted(available_reservoirs):
            checkbox = QCheckBox(f"水库 {reservoir_id}")
            checkbox.setStyleSheet(f"color: {self.color_mapping.get(reservoir_id, 'black')};")
            checkbox.toggled.connect(self.on_reservoir_selection_changed)
            self.reservoir_layout.addWidget(checkbox)

    def update_field_checkboxes(self):
        """更新字段复选框"""
        # 清理现有复选框
        while self.field_layout.count():
            item = self.field_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # 收集所有可用字段
        available_fields = set()
        
        if self.input_data_cb.isChecked():
            for df in self.data_storage['input_data'].values():
                if isinstance(df, pd.DataFrame):
                    available_fields.update(df.columns)
        
        if self.model_results_cb.isChecked():
            for df in self.data_storage['model_results'].values():
                if isinstance(df, pd.DataFrame):
                    available_fields.update(df.columns)
        
        if self.schedule_results_cb.isChecked():
            for df in self.data_storage['schedule_results'].values():
                if isinstance(df, pd.DataFrame):
                    available_fields.update(df.columns)
        
        # 为每个字段创建复选框
        for field in sorted(available_fields):
            checkbox = QCheckBox(field)
            checkbox.toggled.connect(self.on_field_selection_changed)
            self.field_layout.addWidget(checkbox)

    def on_reservoir_selection_changed(self):
        """水库选择变化时的处理"""
        self.update_plot()  # 实时更新图表
    
    def on_field_selection_changed(self):
        """字段选择变化时的处理"""
        self.update_plot()  # 实时更新图表

    def select_all_reservoirs(self):
        """全选水库"""
        for i in range(self.reservoir_layout.count()):
            item = self.reservoir_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                checkbox = item.widget()
                if isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(True)

    def deselect_all_reservoirs(self):
        """全不选水库"""
        for i in range(self.reservoir_layout.count()):
            item = self.reservoir_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                checkbox = item.widget()
                if isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(False)

    def update_plot(self):
        """更新所有图表显示 - 为每个字段创建独立图表"""
        # 获取选中的字段
        selected_fields = self.get_selected_fields()
        
        if not selected_fields:
            self.show_empty_message()
            return
        
        # 清除现有图表
        self.clear_all_charts()
        
        # 为每个字段创建独立的时间序列图
        for field in selected_fields:
            canvas = self.create_field_chart(field)
            self.plot_field_time_series(canvas, field)
        
        # 添加一些间距
        self.scroll_layout.addStretch()

    def plot_field_time_series(self, canvas, field_name):
        """为单个字段绘制时间序列图"""
        canvas.axes.clear()
        
        # 获取选中的水库
        selected_reservoirs = self.get_selected_reservoirs()
        
        if not selected_reservoirs:
            canvas.axes.text(0.5, 0.5, f"请选择水库以显示字段 '{field_name}' 的数据", 
                           ha='center', va='center', transform=canvas.axes.transAxes,
                           fontsize=12, fontfamily='Microsoft YaHei')
            canvas.draw()
            return
        
        has_data = False
        
        # 绘制数据
        for reservoir_id in selected_reservoirs:
            color = self.color_mapping.get(reservoir_id, 'blue')
            
            # 绘制输入数据
            if self.input_data_cb.isChecked() and reservoir_id in self.data_storage['input_data']:
                df = self.data_storage['input_data'][reservoir_id]
                if isinstance(df, pd.DataFrame) and not df.empty and field_name in df.columns:
                    x_data = range(len(df)) if df.index.dtype == 'object' else df.index
                    canvas.axes.plot(x_data, df[field_name], 
                                   label=f"水库{reservoir_id}(输入)", 
                                   color=color, linestyle='-', alpha=0.8, linewidth=2)
                    has_data = True
            
            # 绘制模型结果
            if self.model_results_cb.isChecked() and reservoir_id in self.data_storage['model_results']:
                df = self.data_storage['model_results'][reservoir_id]
                if isinstance(df, pd.DataFrame) and not df.empty and field_name in df.columns:
                    x_data = range(len(df)) if df.index.dtype == 'object' else df.index
                    canvas.axes.plot(x_data, df[field_name], 
                                   label=f"水库{reservoir_id}(模型)", 
                                   color=color, linestyle='--', alpha=0.8, linewidth=2)
                    has_data = True
        
        # 绘制调度结果
        if self.schedule_results_cb.isChecked():
            for result_type, df in self.data_storage['schedule_results'].items():
                if isinstance(df, pd.DataFrame) and not df.empty and field_name in df.columns:
                    x_data = range(len(df)) if df.index.dtype == 'object' else df.index
                    canvas.axes.plot(x_data, df[field_name], 
                                   label=f"调度优化", 
                                   color='red', linestyle=':', alpha=0.8, linewidth=2)
                    has_data = True
        
        if not has_data:
            canvas.axes.text(0.5, 0.5, f"字段 '{field_name}' 无可用数据", 
                           ha='center', va='center', transform=canvas.axes.transAxes,
                           fontsize=12, fontfamily='Microsoft YaHei')
        else:
            # 设置图表标题和标签
            canvas.axes.set_title(f'{field_name} - 时间序列', fontsize=14, fontfamily='Microsoft YaHei', pad=20)
            canvas.axes.set_xlabel('时间步', fontsize=12, fontfamily='Microsoft YaHei')
            canvas.axes.set_ylabel(field_name, fontsize=12, fontfamily='Microsoft YaHei')
            
            # 设置图例
            if canvas.axes.get_legend_handles_labels()[0]:
                canvas.axes.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10, prop={'family': 'Microsoft YaHei'})
            
            # 添加网格
            canvas.axes.grid(True, alpha=0.3)
            
            # 优化布局
            canvas.figure.tight_layout()
        
        canvas.draw()

    def get_selected_reservoirs(self):
        """获取选中的水库ID列表"""
        selected = []
        for i in range(self.reservoir_layout.count()):
            item = self.reservoir_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                checkbox = item.widget()
                if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                    # 从复选框文本中提取水库ID
                    text = checkbox.text()  # "水库 1"
                    reservoir_id = int(text.split()[-1])
                    selected.append(reservoir_id)
        return selected

    def get_selected_fields(self):
        """获取选中的字段列表"""
        selected = []
        for i in range(self.field_layout.count()):
            item = self.field_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                checkbox = item.widget()
                if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                    selected.append(checkbox.text())
        return selected

    # 数据接口方法
    def set_input_data(self, reservoir_data):
        """设置输入数据"""
        if isinstance(reservoir_data, dict):
            self.data_storage['input_data'] = reservoir_data
            self.update_reservoir_checkboxes()
            self.update_field_checkboxes()

    def set_model_results(self, results_data):
        """设置模型结果数据"""
        if isinstance(results_data, dict):
            self.data_storage['model_results'] = results_data
            self.update_reservoir_checkboxes()
            self.update_field_checkboxes()

    def set_schedule_results(self, schedule_data):
        """设置调度优化结果数据"""
        if isinstance(schedule_data, dict):
            self.data_storage['schedule_results'] = schedule_data
            self.update_field_checkboxes()

    # 保持向后兼容的旧接口
    def plot_data(self, data_dict):
        """
        兼容旧接口：根据给定的数据字典绘制图表
        """
        # 将数据存储为单一结果并更新显示
        if isinstance(data_dict, dict):
            self.data_storage['schedule_results']['general'] = pd.DataFrame(data_dict)
            self.schedule_results_cb.setChecked(True)
            self.update_field_checkboxes()
            
            # 自动选择所有字段
            for i in range(self.field_layout.count()):
                item = self.field_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QCheckBox):
                    checkbox = item.widget()
                    if isinstance(checkbox, QCheckBox):
                        checkbox.setChecked(True)
            
            self.update_plot()
    
    def save_all_charts(self):
        """保存所有字段图表为图片文件"""
        if not self.field_charts:
            QMessageBox.information(self, "提示", "没有可保存的图表，请先选择字段并生成图表。")
            return
        
        # 选择保存目录
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", "")
        if not save_dir:
            return
        
        try:
            saved_files = []
            
            # 保存每个字段的图表
            for field_name, canvas in self.field_charts.items():
                # 使用安全的文件名（移除可能的特殊字符）
                safe_field_name = "".join(c for c in field_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = os.path.join(save_dir, f"字段_{safe_field_name}_时间序列图.png")
                
                canvas.figure.savefig(filename, dpi=300, bbox_inches='tight', 
                                    facecolor='white', edgecolor='none')
                saved_files.append(filename)
            
            # 显示成功消息
            field_count = len(saved_files)
            QMessageBox.information(self, "保存成功", 
                                   f"已保存 {field_count} 个字段的图表到:\n{save_dir}\n\n保存的文件:\n" + 
                                   "\n".join([os.path.basename(f) for f in saved_files]))
        
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存图表时发生错误:\n{str(e)}")