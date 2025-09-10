#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
可视化模块 - 独立字段图表系统
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QTextEdit, QCheckBox, QScrollArea, QFrame,
    QSplitter, QGroupBox
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib import rcParams
from .widgets.integrated_chart_widget import IntegratedChartWidget

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

from PyQt6.QtGui import QFont

class VisTab(QWidget):
    """可视化标签页 - 集成图表显示"""
    
    def __init__(self):
        super().__init__()
        self.chart_widgets = []  # 存储图表组件
        self.current_data = None
        
        # 初始化数据属性
        self.input_data = None
        self.model_results = None
        self.schedule_results = None
        # 多水库可视化控制
        self.available_reservoir_ids: list[int] = []
        self.selected_reservoir_ids: set[int] = set()
        self.compare_mode: bool = False
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 控制面板
        control_panel = QGroupBox("控制面板")
        control_layout = QHBoxLayout()
        
        # 数据类型选择
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems([
            "输入数据", "模型结果", "调度优化结果", "所有数据"
        ])
        self.data_type_combo.currentTextChanged.connect(self.on_data_type_changed)
        control_layout.addWidget(QLabel("数据类型:"))
        control_layout.addWidget(self.data_type_combo)
        
        # 水库选择（根据数据动态生成）
        self.compare_checkbox = QCheckBox("对比")
        self.compare_checkbox.setToolTip("开启后，将所有已勾选水库的同名物理量画在同一张图上")
        self.compare_checkbox.stateChanged.connect(self._on_compare_changed)
        control_layout.addWidget(self.compare_checkbox)

        self.res_selector_group = QGroupBox("水库选择")
        self.res_selector_layout = QHBoxLayout(self.res_selector_group)
        self.res_selector_group.setToolTip("仅显示已勾选的水库。水库数量由数据配置页决定。")
        # 占位：首次无数据时不渲染具体勾选项
        self.res_selector_layout.addWidget(QLabel("暂无水库"))
        control_layout.addWidget(self.res_selector_group)
        
        # 操作按钮
        self.refresh_btn = QPushButton("刷新图表")
        self.refresh_btn.clicked.connect(self.refresh_charts)
        control_layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("清除图表")
        self.clear_btn.clicked.connect(self.clear_charts)
        control_layout.addWidget(self.clear_btn)
        
        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)
        
        # 图表显示区域
        charts_group = QGroupBox("图表显示")
        charts_layout = QVBoxLayout()
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 图表容器
        self.charts_container = QWidget()
        self.charts_layout = QVBoxLayout(self.charts_container)
        self.charts_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.charts_container)
        charts_layout.addWidget(self.scroll_area)
        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group)
        
        # 状态栏
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        self.update_status("可视化模块已初始化")
    
    def on_data_type_changed(self, data_type=None):
        """数据类型改变时的处理"""
        if data_type is None:
            data_type = self.data_type_combo.currentText()
        
        self.update_status(f"切换到数据类型: {data_type}")
        
        # 重新构建水库选择器，确保包含当前数据类型中的水库
        self._rebuild_reservoir_selector()
        
        # 根据数据类型显示相应的图表
        if data_type == "调度优化结果":
            self.display_schedule_results()
        elif data_type == "模型结果":
            self.display_model_results()
        elif data_type == "输入数据":
            self.display_input_data()
        elif data_type == "所有数据":
            self.display_all_data()

    # ------------------------- 多水库控制 -------------------------
    def _on_compare_changed(self):
        self.compare_mode = self.compare_checkbox.isChecked()
        self.refresh_charts()

    def _rebuild_reservoir_selector(self):
        """根据当前数据重建水库勾选项。"""
        # 计算可用水库ID（来自输入、模型结果或调度优化结果）
        ids = set()
        if isinstance(self.input_data, dict):
            ids.update(self.input_data.keys())
        if isinstance(self.model_results, dict):
            ids.update(self.model_results.keys())
        if hasattr(self, 'schedule_results') and isinstance(self.schedule_results, dict):
            # 从调度优化结果中获取水库ID
            optimization_results = self.schedule_results.get('optimization_results')
            if optimization_results is not None and not optimization_results.empty:
                if 'reservoir_id' in optimization_results.columns:
                    schedule_ids = set(optimization_results['reservoir_id'].unique())
                    ids.update(schedule_ids)
        
        self.available_reservoir_ids = sorted(int(i) for i in ids)
        
        # 添加调试信息
        self.update_status(f"重建水库选择器，可用水库ID: {self.available_reservoir_ids}")

        # 清空原有控件
        while self.res_selector_layout.count():
            item = self.res_selector_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        if not self.available_reservoir_ids:
            self.res_selector_layout.addWidget(QLabel("暂无水库"))
            self.selected_reservoir_ids = set()
            return

        # 先初始化选中状态
        self.selected_reservoir_ids = set(self.available_reservoir_ids)
        
        # 全选/全不选
        select_all_cb = QCheckBox("全选")
        select_all_cb.setChecked(True)  # 先设置状态，再绑定信号
        
        def _toggle_all(state):
            checked = state == Qt.CheckState.Checked
            # 更新选中状态
            if checked:
                self.selected_reservoir_ids = set(self.available_reservoir_ids)
            else:
                self.selected_reservoir_ids = set()
            
            # 更新所有水库复选框状态
            for i in range(1, self.res_selector_layout.count()):
                item_i = self.res_selector_layout.itemAt(i)
                if item_i is None:
                    continue
                w = item_i.widget()
                if isinstance(w, QCheckBox):
                    w.blockSignals(True)
                    w.setChecked(checked)
                    w.blockSignals(False)
            
            self.update_status(f"全选状态改变，选中水库: {self.selected_reservoir_ids}")
            self.refresh_charts()
        
        # 绑定全选信号
        select_all_cb.stateChanged.connect(_toggle_all)
        self.res_selector_layout.addWidget(select_all_cb)

        # 逐个水库复选框
        def _on_one_changed(res_id: int, state: int):
            if state == Qt.CheckState.Checked:
                self.selected_reservoir_ids.add(res_id)
            else:
                self.selected_reservoir_ids.discard(res_id)
            
            # 更新全选复选框状态
            if len(self.selected_reservoir_ids) == len(self.available_reservoir_ids):
                select_all_cb.setChecked(True)
            elif len(self.selected_reservoir_ids) == 0:
                select_all_cb.setChecked(False)
            else:
                select_all_cb.setChecked(False)
            
            self.update_status(f"水库{res_id}选择状态改变，当前选中: {self.selected_reservoir_ids}")
            self.refresh_charts()

        # 添加调试信息
        self.update_status(f"水库选择器重建完成，默认选中: {self.selected_reservoir_ids}")

        for res_id in self.available_reservoir_ids:
            cb = QCheckBox(f"水库{res_id}")
            cb.setChecked(True)
            # 绑定变化
            cb.stateChanged.connect(lambda state, rid=res_id: _on_one_changed(rid, state))
            self.res_selector_layout.addWidget(cb)
    
    def display_schedule_results(self):
        """显示调度优化结果"""
        if not hasattr(self, 'schedule_results') or self.schedule_results is None:
            self.update_status("没有调度优化结果数据")
            return
        
        self.clear_charts()
        
        try:
            # 获取优化结果数据
            optimization_results = self.schedule_results.get('optimization_results')
            if optimization_results is None or optimization_results.empty:
                self.update_status("没有找到调度优化结果数据")
                return
            
            # 检查是否包含水库ID字段
            if 'reservoir_id' not in optimization_results.columns:
                self.update_status("调度优化结果缺少水库ID字段，无法按水库分类")
                return
            
            # 获取所有水库ID
            reservoir_ids = sorted(optimization_results['reservoir_id'].unique())
            self.update_status(f"检测到 {len(reservoir_ids)} 个水库的调度优化结果")
            
            # 检查是否有选中的水库
            chosen = list(self.selected_reservoir_ids)
            self.update_status(f"当前选中的水库: {chosen}")
            self.update_status(f"可用水库ID: {self.available_reservoir_ids}")
            
            if not chosen:
                self.update_status("未选择任何水库")
                return
            
            # 筛选选中的水库数据
            selected_reservoir_ids = [rid for rid in reservoir_ids if rid in chosen]
            if not selected_reservoir_ids:
                self.update_status("选中的水库在调度结果中未找到")
                return
            
            if self.compare_mode:
                # 对比模式：将所有选中水库的同名物理量画在同一张图上
                self.update_status("对比模式：正在创建对比图表...")
                self.update_status(f"对比模式：选中的水库ID: {selected_reservoir_ids}")
                
                # 对比目标函数结果
                objectives = self.schedule_results.get('objectives')
                self.update_status(f"对比模式：目标函数数据存在: {objectives is not None}")
                if objectives is not None and not objectives.empty:
                    self.update_status(f"对比模式：目标函数数据形状: {objectives.shape}")
                    self.update_status(f"对比模式：目标函数列名: {list(objectives.columns)}")
                    if 'reservoir_id' in objectives.columns:
                        self.update_status("对比模式：目标函数数据包含水库ID字段")
                        for col in objectives.columns:
                            if col in ['flood', 'power', 'supply', 'ecology']:
                                self.update_status(f"对比模式：正在处理目标函数: {col}")
                                # 创建对比数据框
                                compare_data = {}
                                for rid in selected_reservoir_ids:
                                    reservoir_objectives = objectives[objectives['reservoir_id'] == rid]
                                    self.update_status(f"对比模式：水库{rid}的目标函数数据形状: {reservoir_objectives.shape}")
                                    if not reservoir_objectives.empty and col in reservoir_objectives.columns:
                                        compare_data[f"水库{rid}"] = reservoir_objectives[col]
                                        self.update_status(f"对比模式：水库{rid}的{col}数据长度: {len(reservoir_objectives[col])}")
                                    else:
                                        self.update_status(f"对比模式：水库{rid}的{col}数据为空或不存在")
                                
                                self.update_status(f"对比模式：{col}目标函数的对比数据: {list(compare_data.keys())}")
                                if len(compare_data) > 1:  # 至少有两个水库的数据才创建对比图
                                    compare_df = pd.DataFrame(compare_data)
                                    self.update_status(f"对比模式：创建{col}目标对比图，数据形状: {compare_df.shape}")
                                    chart_widget = IntegratedChartWidget(f"对比-调度优化-{col}", compare_df)
                                    self.charts_layout.addWidget(chart_widget)
                                    self.chart_widgets.append(chart_widget)
                                    self.update_status(f"已创建调度优化{col}目标对比图")
                                else:
                                    self.update_status(f"对比模式：{col}目标函数数据不足，无法创建对比图")
                    else:
                        self.update_status("对比模式：目标函数数据缺少水库ID字段")
                else:
                    self.update_status("对比模式：没有目标函数数据")
                
                # 对比决策变量
                self.update_status("对比模式：开始处理决策变量...")
                common_decision_vars = None
                for rid in selected_reservoir_ids:
                    reservoir_data = optimization_results[optimization_results['reservoir_id'] == rid]
                    self.update_status(f"对比模式：水库{rid}的决策变量数据形状: {reservoir_data.shape}")
                    if not reservoir_data.empty:
                        objectives_cols = list(objectives.columns) if objectives is not None else []
                        # 修复决策变量识别：排除已知列，保留其他列作为决策变量
                        excluded_cols = ['reservoir_id', 'time_step'] + objectives_cols
                        decision_vars = [col for col in reservoir_data.columns if col not in excluded_cols]
                        self.update_status(f"对比模式：水库{rid}的决策变量: {decision_vars}")
                        if common_decision_vars is None:
                            common_decision_vars = set(decision_vars)
                        else:
                            common_decision_vars &= set(decision_vars)
                
                self.update_status(f"对比模式：公共决策变量: {common_decision_vars}")
                if common_decision_vars:
                    for var in sorted(common_decision_vars):
                        self.update_status(f"对比模式：正在处理决策变量: {var}")
                        compare_data = {}
                        for rid in selected_reservoir_ids:
                            reservoir_data = optimization_results[optimization_results['reservoir_id'] == rid]
                            if not reservoir_data.empty and var in reservoir_data.columns:
                                compare_data[f"水库{rid}"] = reservoir_data[var]
                                self.update_status(f"对比模式：水库{rid}的{var}数据长度: {len(reservoir_data[var])}")
                        
                        if len(compare_data) > 1:
                            compare_df = pd.DataFrame(compare_data)
                            self.update_status(f"对比模式：创建{var}决策变量对比图，数据形状: {compare_df.shape}")
                            chart_widget = IntegratedChartWidget(f"对比-决策变量-{var}", compare_df)
                            self.charts_layout.addWidget(chart_widget)
                            self.chart_widgets.append(chart_widget)
                            self.update_status(f"已创建决策变量{var}对比图")
                        else:
                            self.update_status(f"对比模式：决策变量{var}数据不足，无法创建对比图")
                else:
                    self.update_status("对比模式：没有找到公共决策变量")
                
                # 对比帕累托前沿（如果存在）
                if 'pareto_front' in self.schedule_results:
                    self.update_status("对比模式：开始处理帕累托前沿...")
                    pareto_data = self.schedule_results['pareto_front']
                    if isinstance(pareto_data, pd.DataFrame) and len(pareto_data) > 0:
                        self.update_status(f"对比模式：帕累托前沿数据形状: {pareto_data.shape}")
                        if 'reservoir_id' in pareto_data.columns:
                            self.update_status("对比模式：帕累托前沿数据包含水库ID字段")
                            # 为每个目标函数创建对比图
                            objectives = self.schedule_results.get('objectives')
                            if objectives is not None and not objectives.empty:
                                for col in objectives.columns:
                                    if col in ['flood', 'power', 'supply', 'ecology']:
                                        self.update_status(f"对比模式：正在处理帕累托前沿的{col}目标")
                                        compare_data = {}
                                        for rid in selected_reservoir_ids:
                                            reservoir_pareto = pareto_data[pareto_data['reservoir_id'] == rid]
                                            self.update_status(f"对比模式：水库{rid}的帕累托前沿数据形状: {reservoir_pareto.shape}")
                                            if not reservoir_pareto.empty and col in reservoir_pareto.columns:
                                                compare_data[f"水库{rid}"] = reservoir_pareto[col]
                                                self.update_status(f"对比模式：水库{rid}的帕累托前沿{col}数据长度: {len(reservoir_pareto[col])}")
                                        
                                        if len(compare_data) > 1:
                                            compare_df = pd.DataFrame(compare_data)
                                            self.update_status(f"对比模式：创建帕累托前沿{col}对比图，数据形状: {compare_df.shape}")
                                            chart_widget = IntegratedChartWidget(f"对比-帕累托前沿-{col}", compare_df)
                                            self.charts_layout.addWidget(chart_widget)
                                            self.chart_widgets.append(chart_widget)
                                            self.update_status(f"已创建帕累托前沿{col}对比图")
                                        else:
                                            self.update_status(f"对比模式：帕累托前沿{col}数据不足，无法创建对比图")
                        else:
                            self.update_status("对比模式：帕累托前沿数据缺少水库ID字段")
                    else:
                        self.update_status("对比模式：帕累托前沿数据为空或格式错误")
                else:
                    self.update_status("对比模式：没有帕累托前沿数据")
                
                self.update_status(f"对比模式：图表创建完成，共 {len(self.chart_widgets)} 个图表")
                
            else:
                # 分通道模式（按水库独立显示）
                for reservoir_id in selected_reservoir_ids:
                    # 筛选当前水库的数据
                    reservoir_data = optimization_results[optimization_results['reservoir_id'] == reservoir_id]
                    
                    if reservoir_data.empty:
                        continue
                    
                    self.update_status(f"正在显示水库 {reservoir_id} 的调度优化结果...")
                    
                    # 显示目标函数结果
                    objectives = self.schedule_results.get('objectives')
                    if objectives is not None and not objectives.empty:
                        # 筛选当前水库的目标函数数据
                        for col in objectives.columns:
                            if col in ['flood', 'power', 'supply', 'ecology']:
                                # 筛选当前水库的目标函数数据
                                if 'reservoir_id' in objectives.columns:
                                    reservoir_objectives = objectives[objectives['reservoir_id'] == reservoir_id]
                                    if not reservoir_objectives.empty:
                                        chart_widget = IntegratedChartWidget(
                                            f"水库{reservoir_id}-调度优化-{col}", 
                                            reservoir_objectives[col]
                                        )
                                        self.charts_layout.addWidget(chart_widget)
                                        self.chart_widgets.append(chart_widget)
                                        self.update_status(f"已创建水库{reservoir_id}的{col}目标图表")
                                else:
                                    # 如果没有水库ID字段，显示所有数据
                                    chart_widget = IntegratedChartWidget(
                                        f"水库{reservoir_id}-调度优化-{col}", 
                                        objectives[col]
                                    )
                                    self.charts_layout.addWidget(chart_widget)
                                    self.chart_widgets.append(chart_widget)
                                    self.update_status(f"已创建水库{reservoir_id}的{col}目标图表")
                    
                    # 显示当前水库的帕累托前沿（如果存在）
                    if 'pareto_front' in self.schedule_results:
                        pareto_data = self.schedule_results['pareto_front']
                        if isinstance(pareto_data, pd.DataFrame) and len(pareto_data) > 0:
                            # 筛选当前水库的帕累托前沿数据
                            if 'reservoir_id' in pareto_data.columns:
                                reservoir_pareto = pareto_data[pareto_data['reservoir_id'] == reservoir_id]
                                if not reservoir_pareto.empty:
                                    chart_widget = IntegratedChartWidget(f"水库{reservoir_id}-帕累托前沿", reservoir_pareto)
                                    self.charts_layout.addWidget(chart_widget)
                                    self.chart_widgets.append(chart_widget)
                                    self.update_status(f"已创建水库{reservoir_id}的帕累托前沿图表")
                            else:
                                # 如果没有水库ID字段，显示所有数据
                                chart_widget = IntegratedChartWidget(f"水库{reservoir_id}-帕累托前沿", pareto_data)
                                self.charts_layout.addWidget(chart_widget)
                                self.chart_widgets.append(chart_widget)
                                self.update_status(f"已创建水库{reservoir_id}的帕累托前沿图表")
                    
                    # 显示当前水库的决策变量（调度策略）
                    objectives_cols = list(objectives.columns) if objectives is not None else []
                    # 修复决策变量识别：排除已知列，保留其他列作为决策变量
                    excluded_cols = ['reservoir_id', 'time_step'] + objectives_cols
                    decision_vars = [col for col in reservoir_data.columns if col not in excluded_cols]
                    
                    if decision_vars:
                        for var in decision_vars:
                            chart_widget = IntegratedChartWidget(f"水库{reservoir_id}-决策变量-{var}", reservoir_data[[var]])
                            self.charts_layout.addWidget(chart_widget)
                            self.chart_widgets.append(chart_widget)
                            self.update_status(f"已创建水库{reservoir_id}的决策变量{var}图表")
                    else:
                        self.update_status(f"水库{reservoir_id}没有可显示的决策变量")
            
            self.update_status(f"调度优化结果显示完成，共 {len(self.chart_widgets)} 个图表")
            
        except Exception as e:
            self.update_status(f"显示调度结果时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def display_model_results(self):
        """显示模型结果"""
        if not hasattr(self, 'model_results') or self.model_results is None:
            self.update_status("没有模型结果数据")
            return
        
        self.clear_charts()
        try:
            # 无选择时不绘制
            chosen = list(self.selected_reservoir_ids)
            if not chosen:
                self.update_status("未选择任何水库")
                return
            if self.compare_mode:
                # 找到所有选择水库的公共列
                common_cols = None
                for rid in chosen:
                    df = self.model_results.get(rid)
                    if isinstance(df, pd.DataFrame):
                        cols = set(c for c in df.columns if c not in ['time_step', 'reservoir_id'])
                        common_cols = cols if common_cols is None else (common_cols & cols)
                if not common_cols:
                    self.update_status("对比模式：未找到公共物理量可用于对比")
                    return
                for col in sorted(common_cols):
                    compare_df = pd.DataFrame({f"水库{rid}": self.model_results[rid][col] for rid in chosen})
                    chart_widget = IntegratedChartWidget(f"对比-{col}", compare_df)
                    self.charts_layout.addWidget(chart_widget)
                    self.chart_widgets.append(chart_widget)
                    self.update_status(f"已创建 {col} 对比图")
            else:
                # 分通道（按水库独立）
                for reservoir_id, results_df in self.model_results.items():
                    if reservoir_id not in chosen:
                        continue
                    if isinstance(results_df, pd.DataFrame) and not results_df.empty:
                        for col in results_df.columns:
                            if col not in ['time_step', 'reservoir_id']:
                                chart_widget = IntegratedChartWidget(f"水库{reservoir_id}-{col}", results_df[col])
                                self.charts_layout.addWidget(chart_widget)
                                self.chart_widgets.append(chart_widget)
                                self.update_status(f"已创建水库{reservoir_id}的{col}图表")

            self.update_status(f"模型结果显示完成，共 {len(self.chart_widgets)} 个图表")
        except Exception as e:
            self.update_status(f"显示模型结果时出错: {str(e)}")
    
    def display_input_data(self):
        """显示输入数据"""
        if not hasattr(self, 'input_data') or self.input_data is None:
            self.update_status("没有输入数据")
            return
        
        self.clear_charts()
        try:
            # 无选择时不绘制
            chosen = list(self.selected_reservoir_ids)
            if not chosen:
                self.update_status("未选择任何水库")
                return
            if self.compare_mode:
                # 找公共列
                common_cols = None
                for rid in chosen:
                    df = self.input_data.get(rid)
                    if isinstance(df, pd.DataFrame):
                        cols = set(c for c in df.columns if c not in ['time_step', 'reservoir_id'])
                        common_cols = cols if common_cols is None else (common_cols & cols)
                if not common_cols:
                    self.update_status("对比模式：未找到公共物理量可用于对比")
                    return
                for col in sorted(common_cols):
                    compare_df = pd.DataFrame({f"水库{rid}": self.input_data[rid][col] for rid in chosen})
                    chart_widget = IntegratedChartWidget(f"对比(输入)-{col}", compare_df)
                    self.charts_layout.addWidget(chart_widget)
                    self.chart_widgets.append(chart_widget)
                    self.update_status(f"已创建 输入 {col} 对比图")
            else:
                for reservoir_id, input_df in self.input_data.items():
                    if reservoir_id not in chosen:
                        continue
                    if isinstance(input_df, pd.DataFrame) and not input_df.empty:
                        for col in input_df.columns:
                            if col not in ['time_step', 'reservoir_id']:
                                chart_widget = IntegratedChartWidget(f"水库{reservoir_id}输入-{col}", input_df[col])
                                self.charts_layout.addWidget(chart_widget)
                                self.chart_widgets.append(chart_widget)
                                self.update_status(f"已创建水库{reservoir_id}输入{col}图表")

            self.update_status(f"输入数据显示完成，共 {len(self.chart_widgets)} 个图表")
        except Exception as e:
            self.update_status(f"显示输入数据时出错: {str(e)}")
    
    def display_all_data(self):
        """显示所有数据"""
        self.update_status("开始显示所有数据...")
        
        # 显示输入数据
        if hasattr(self, 'input_data') and self.input_data:
            self.display_input_data()
        
        # 显示模型结果
        if hasattr(self, 'model_results') and self.model_results:
            self.display_model_results()
        
        # 显示调度优化结果
        if hasattr(self, 'schedule_results') and self.schedule_results:
            self.display_schedule_results()
        
        self.update_status("所有数据显示完成")
    
    def refresh_charts(self):
        """刷新图表"""
        # 依据当前数据类型重绘，应用勾选与对比模式
        data_type = self.data_type_combo.currentText()
        if data_type == "输入数据":
            self.display_input_data()
        elif data_type == "模型结果":
            self.display_model_results()
        elif data_type == "调度优化结果":
            self.display_schedule_results()
        else:
            self.display_all_data()
    
    def clear_charts(self):
        """清除所有图表"""
        for widget in self.chart_widgets:
            widget.deleteLater()
        self.chart_widgets.clear()
        self.update_status("已清除所有图表")
    
    def update_status(self, message):
        """更新状态信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
    
    # 保持向后兼容的接口方法
    def plot_data(self, data_dict):
        """绘制数据的接口方法（保持向后兼容）"""
        self.update_status("使用集成图表模式")
        return True
    
    def set_input_data(self, reservoir_data):
        """设置输入数据（保持向后兼容）"""
        if isinstance(reservoir_data, dict):
            self.input_data = reservoir_data
            self.update_status(f"收到输入数据，包含 {len(reservoir_data)} 个水库")
            # 重新构建水库选择器
            self._rebuild_reservoir_selector()
            # 自动切换到输入数据类型并显示
            self.data_type_combo.setCurrentText("输入数据")
            self.on_data_type_changed()
            return True
        else:
            self.update_status("输入数据格式错误")
            return False
    
    def set_model_results(self, reservoir_results):
        """设置模型结果数据（保持向后兼容）"""
        if isinstance(reservoir_results, dict):
            self.model_results = reservoir_results
            self.update_status(f"收到模型结果数据，包含 {len(reservoir_results)} 个水库")
            # 重新构建水库选择器
            self._rebuild_reservoir_selector()
            # 自动切换到模型结果数据类型并显示
            self.data_type_combo.setCurrentText("模型结果")
            self.on_data_type_changed()
            return True
        else:
            self.update_status("模型结果数据格式错误")
            return False
    
    def set_schedule_results(self, schedule_results):
        """设置调度优化结果数据（保持向后兼容）"""
        if isinstance(schedule_results, dict):
            self.update_status(f"收到调度优化结果")
            
            # 存储调度结果数据
            self.schedule_results = schedule_results
            
            # 重新构建水库选择器
            self._rebuild_reservoir_selector()
            
            # 自动切换到调度优化结果数据类型并显示
            self.data_type_combo.setCurrentText("调度优化结果")
            self.on_data_type_changed()
            
            return True
        else:
            self.update_status("调度优化结果数据格式错误")
            return False
    
    def update_plot(self):
        """更新图表显示（保持向后兼容）"""
        self.refresh_charts()
        return True