from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLineEdit, QLabel, QPushButton, QFormLayout, QGroupBox, QStyle, QApplication, QSpinBox, QDoubleSpinBox, QTabWidget, QScrollArea, QTextEdit, QHBoxLayout, QMessageBox, QCheckBox
from PyQt6.QtGui import QIcon
from .icon_utils import load_icon
from .ui_utils import MODEL_DATA_REQUIREMENTS, TRANSLATIONS
from PyQt6.QtCore import pyqtSignal, Qt
import os
import sys

# 定义模型所需的参数
MODEL_PARAMS = {
    "SCS-CN": {
        "basic": {
            "CN": "径流曲线数",
            "Ia_coefficient": "初始抽象量系数",
            "land_use": "土地利用类型",
            "soil_type": "土壤类型",
            "vegetation_cover": "植被覆盖度",
            "slope": "坡度 (%)"
        },
        "climate": {
            "antecedent_days": "前期降雨天数",
            "auto_calculate_antecedent": "自动计算前期降雨量",
            "antecedent_rainfall": "前期降雨量 (mm) - 手动设置",
            "temperature": "温度 (℃)",
            "evaporation": "蒸发量 (mm)"
        }
    },
    "Saint-Venant": {
        "basic": {
            "dx": "空间步长 (m)",
            "dt": "时间步长 (s)",
            "nx": "空间网格数",
            "nt": "时间网格数",
            "manning_n": "Manning粗糙系数",
            "channel_width": "渠道宽度 (m)",
            "channel_slope": "渠道坡度"
        },
        "channel_shape": {
            "channel_shape": "渠道形状",
            "side_slope": "边坡系数",
            "parabola_coefficient": "抛物线系数",
            "radius": "圆形渠道半径 (m)"
        },
        "initial_conditions": {
            "initial_depth": "初始水深 (m)",
            "initial_velocity": "初始流速 (m/s)"
        },
        "lateral_flow": {
            "lateral_inflow": "侧向入流 (m³/s/m)",
            "lateral_outflow": "侧向出流 (m³/s/m)"
        },
        "optional_features": {
            "enable_lateral_flow": "启用侧向流",
            "enable_wind_effects": "启用风应力效应",
            "enable_temperature_effects": "启用温度效应"
        }
    },
    "其他模型...": {"param_a": "参数A", "param_b": "参数B"}
}

class ModelTab(QWidget):
    """
    '模型配置'选项卡的UI界面。
    参数配置区域会根据所选模型动态更新，支持完整的专业参数配置。
    """
    model_selection_changed = pyqtSignal(str)
    example_params_requested = pyqtSignal(str)  # 请求加载示例参数

    def __init__(self):
        super().__init__()
        self.param_widgets = {} # { "param_name": QLineEdit, ... }
        self.current_model = ""
        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        
        # 模型选择
        model_selection_layout = QFormLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems([""] + list(MODEL_PARAMS.keys()))
        # 为每个模型项设置提示
        for idx in range(1, self.model_combo.count()):
            model_name = self.model_combo.itemText(idx)
            if model_name in MODEL_DATA_REQUIREMENTS:
                reqs = MODEL_DATA_REQUIREMENTS[model_name]
                translated = [TRANSLATIONS.get(r, r) for r in reqs]
                tooltip = "需要数据: " + ", ".join(translated)
                self.model_combo.setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_selection_layout.addRow(QLabel("选择模型:"), self.model_combo)
        self.main_layout.addLayout(model_selection_layout)

        # 示例数据和参数按钮组
        self.create_example_buttons_group()
        
        # 参数配置区域
        self.params_groupbox = QGroupBox("参数配置")
        self.params_layout = QVBoxLayout()
        self.params_groupbox.setLayout(self.params_layout)
        self.main_layout.addWidget(self.params_groupbox)
        
        # 运行按钮
        self.run_button = QPushButton("运行模型")
        self.run_button.setIcon(load_icon("run.png", "media-playback-start"))
        self.main_layout.addWidget(self.run_button)
        self.main_layout.addStretch()

        self.setLayout(self.main_layout)
        self.on_model_changed("") # 初始状态

    def create_example_buttons_group(self):
        """创建示例参数按钮组"""
        self.example_groupbox = QGroupBox("示例参数")
        self.example_groupbox.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF6B35;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF6B35;
            }
        """)
        
        group_layout = QVBoxLayout(self.example_groupbox)
        
        # 说明标签
        info_label = QLabel("选择模型后，可以快速加载示例参数进行测试")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        group_layout.addWidget(info_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 使用示例参数按钮
        self.use_example_params_btn = QPushButton("使用示例参数")
        self.use_example_params_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #E5E7EB;
                color: #9CA3AF;
            }
        """)
        self.use_example_params_btn.clicked.connect(self.on_use_example_params)
        self.use_example_params_btn.setEnabled(False)
        
        button_layout.addWidget(self.use_example_params_btn)
        button_layout.addStretch()
        
        group_layout.addLayout(button_layout)
        
        # 示例信息显示区域
        self.example_info_label = QLabel("请先选择模型")
        self.example_info_label.setStyleSheet("color: #6B7280; font-size: 10px; padding: 5px;")
        self.example_info_label.setWordWrap(True)
        group_layout.addWidget(self.example_info_label)
        
        # 将示例按钮组添加到主布局
        self.main_layout.addWidget(self.example_groupbox)



    def on_use_example_params(self):
        """使用示例参数按钮点击事件"""
        if self.current_model:
            reply = QMessageBox.question(
                self, 
                "确认加载示例参数", 
                f"确定要加载 {self.current_model} 模型的示例参数吗？\n\n这将覆盖当前的参数设置。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.load_example_params(self.current_model)

    def load_example_params(self, model_name):
        """加载示例参数"""
        try:
            # 导入示例参数
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from example_data.example_parameters import SCS_CN_EXAMPLE_PARAMS, SAINT_VENANT_EXAMPLE_PARAMS
            
            # 根据模型选择对应的示例参数
            if model_name == "SCS-CN":
                example_params = SCS_CN_EXAMPLE_PARAMS
            elif model_name == "Saint-Venant":
                example_params = SAINT_VENANT_EXAMPLE_PARAMS
            else:
                QMessageBox.warning(self, "警告", f"未找到 {model_name} 模型的示例参数")
                return
            
            # 应用示例参数到UI控件
            self.apply_example_params(example_params)
            
            QMessageBox.information(self, "成功", f"{model_name} 模型示例参数已加载")
            
        except ImportError as e:
            QMessageBox.critical(self, "错误", f"无法导入示例参数文件: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载示例参数时发生错误: {str(e)}")

    def apply_example_params(self, example_params):
        """将示例参数应用到UI控件"""
        for category_name, category_params in example_params.items():
            if isinstance(category_params, dict):
                for param_id, value in category_params.items():
                    if param_id in self.param_widgets:
                        widget = self.param_widgets[param_id]
                        if isinstance(widget, QDoubleSpinBox):
                            widget.setValue(float(value))
                        elif isinstance(widget, QSpinBox):
                            widget.setValue(int(value))
                        elif isinstance(widget, QComboBox):
                            widget.setCurrentText(str(value))
                        elif isinstance(widget, QLineEdit):
                            widget.setText(str(value))
                        elif isinstance(widget, QCheckBox):
                            widget.setChecked(bool(value))

    def on_model_changed(self, model_name):
        """当模型选择变化时，重建参数UI并发射信号。"""
        self.current_model = model_name
        
        # 清理旧的参数控件
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.param_widgets.clear()

        # 根据新模型创建参数控件
        if model_name and model_name in MODEL_PARAMS:
            params = MODEL_PARAMS[model_name]
            self._create_parameter_widgets(params)
            self.params_groupbox.setVisible(True)
            
            # 更新示例按钮状态
            self.update_example_buttons_state(model_name)
        else:
            self.params_groupbox.setVisible(False)
            self.update_example_buttons_state("")

        # 发射信号，通知其他模块模型已更改
        self.model_selection_changed.emit(model_name)

    def update_example_buttons_state(self, model_name):
        """更新示例按钮的状态"""
        # 检查是否有示例参数
        has_example_params = model_name in ["SCS-CN", "Saint-Venant"]
        
        # 启用/禁用按钮
        self.use_example_params_btn.setEnabled(has_example_params)
        
        # 更新信息标签
        if model_name == "SCS-CN":
            self.example_info_label.setText(
                "SCS-CN模型示例参数：\n"
                "• 适用于中等渗透性土壤的参数设置\n"
                "• 包含基本参数、土地利用和气候参数"
            )
        elif model_name == "Saint-Venant":
            self.example_info_label.setText(
                "圣维南模型示例参数：\n"
                "• 适用于矩形渠道的数值计算参数\n"
                "• 包含基本参数、渠道形状和环境参数"
            )
        else:
            self.example_info_label.setText("请先选择模型")

    def _create_parameter_widgets(self, params):
        """创建参数控件"""
        if isinstance(params, dict):
            # 检查是否有子分类
            has_subcategories = any(isinstance(v, dict) for v in params.values())
            
            if has_subcategories:
                # 创建选项卡界面
                tab_widget = QTabWidget()
                
                for category_name, category_params in params.items():
                    if isinstance(category_params, dict):
                        # 创建分类页面
                        category_widget = QWidget()
                        category_layout = QFormLayout()
                        
                        for param_id, display_name in category_params.items():
                            if category_name == "optional_features":
                                # 可选功能使用复选框
                                widget = QCheckBox()
                                widget.setChecked(False)
                                widget.setToolTip(display_name)
                                self.param_widgets[param_id] = widget
                                category_layout.addRow(f"{display_name}:", widget)
                            elif category_name in ["lateral_flow"]:
                                # 侧向流参数：复选框 + 数值输入
                                container = QWidget()
                                container_layout = QHBoxLayout(container)
                                container_layout.setContentsMargins(0, 0, 0, 0)
                                
                                # 复选框
                                checkbox = QCheckBox("启用")
                                checkbox.setChecked(False)
                                self.param_widgets[f"{param_id}_enabled"] = checkbox
                                
                                # 数值输入
                                value_widget = self._create_parameter_widget(param_id, display_name)
                                value_widget.setEnabled(False)  # 初始禁用
                                self.param_widgets[param_id] = value_widget
                                
                                # 连接信号
                                checkbox.toggled.connect(value_widget.setEnabled)
                                
                                container_layout.addWidget(checkbox)
                                container_layout.addWidget(value_widget)
                                category_layout.addRow(f"{display_name}:", container)
                            elif category_name == "climate" and param_id == "antecedent_rainfall":
                                # 前期降雨量参数：根据自动计算选项动态显示
                                container = QWidget()
                                container_layout = QHBoxLayout(container)
                                container_layout.setContentsMargins(0, 0, 0, 0)
                                
                                # 数值输入
                                value_widget = self._create_parameter_widget(param_id, display_name)
                                value_widget.setEnabled(False)  # 初始禁用
                                self.param_widgets[param_id] = value_widget
                                
                                # 说明标签
                                info_label = QLabel("(仅在关闭自动计算时可用)")
                                info_label.setStyleSheet("color: #6B7280; font-size: 10px;")
                                
                                container_layout.addWidget(value_widget)
                                container_layout.addWidget(info_label)
                                category_layout.addRow(f"{display_name}:", container)
                                
                                # 存储引用以便后续控制
                                self.antecedent_rainfall_widget = value_widget
                            else:
                                # 普通参数
                                widget = self._create_parameter_widget(param_id, display_name)
                                category_layout.addRow(f"{display_name}:", widget)
                                self.param_widgets[param_id] = widget
                        
                        category_widget.setLayout(category_layout)
                        tab_widget.addTab(category_widget, self._get_category_display_name(category_name))
                
                self.params_layout.addWidget(tab_widget)
                
                # 添加智能控制逻辑
                self._setup_smart_controls()
            else:
                # 简单参数列表
                form_layout = QFormLayout()
                for param_id, display_name in params.items():
                    widget = self._create_parameter_widget(param_id, display_name)
                    form_layout.addRow(f"{display_name}:", widget)
                    self.param_widgets[param_id] = widget
                
                self.params_layout.addLayout(form_layout)

    def _setup_smart_controls(self):
        """设置智能控制逻辑"""
        # 连接自动计算前期降雨量选项的信号
        if 'auto_calculate_antecedent' in self.param_widgets:
            auto_calc_widget = self.param_widgets['auto_calculate_antecedent']
            auto_calc_widget.toggled.connect(self._on_auto_calculate_changed)
            
            # 初始状态设置
            self._on_auto_calculate_changed(auto_calc_widget.isChecked())

    def _on_auto_calculate_changed(self, auto_calculate: bool):
        """当自动计算选项改变时的处理"""
        if hasattr(self, 'antecedent_rainfall_widget'):
            # 启用/禁用前期降雨量手动输入
            self.antecedent_rainfall_widget.setEnabled(not auto_calculate)
            
            # 更新提示信息
            if auto_calculate:
                self.antecedent_rainfall_widget.setToolTip("系统将根据降雨数据自动计算前期降雨量")
            else:
                self.antecedent_rainfall_widget.setToolTip("请输入前期降雨量值")

    def _create_parameter_widget(self, param_id, display_name):
        """创建单个参数控件"""
        # 根据参数类型创建不同的控件
        if param_id in ["CN", "Ia_coefficient", "manning_n", "channel_slope", "vegetation_cover", 
                       "antecedent_rainfall", "temperature", "evaporation", "lateral_inflow", 
                       "lateral_outflow", "wind_speed", "wind_direction", "water_temperature"]:
            # 浮点数参数
            widget = QDoubleSpinBox()
            widget.setRange(0, 10000)
            widget.setDecimals(3)
            widget.setValue(self._get_default_value(param_id))
            widget.setSuffix(self._get_unit_suffix(param_id))
            widget.setToolTip(display_name)
            
        elif param_id in ["dx", "dt", "nx", "nt", "channel_width", "side_slope", 
                         "parabola_coefficient", "radius", "slope", "antecedent_days"]:
            # 浮点数参数（无上限）
            widget = QDoubleSpinBox()
            widget.setRange(0, 999999)
            widget.setDecimals(3)
            widget.setValue(self._get_default_value(param_id))
            widget.setSuffix(self._get_unit_suffix(param_id))
            widget.setToolTip(display_name)
            
        elif param_id in ["land_use", "soil_type", "channel_shape"]:
            # 下拉选择参数
            widget = QComboBox()
            if param_id == "land_use":
                widget.addItems(["行作物", "小粒谷物", "牧草", "林地", "湿地", "森林", "草地", "灌木", "裸地", "城市建成区"])
            elif param_id == "soil_type":
                widget.addItems(["A", "B", "C", "D"])
            elif param_id == "channel_shape":
                widget.addItems(["矩形", "梯形", "三角形", "抛物线形", "圆形"])
            widget.setCurrentText(self._get_default_value(param_id))
            widget.setToolTip(display_name)
            
        elif param_id == "auto_calculate_antecedent":
            # 布尔值参数（复选框）
            widget = QCheckBox()
            widget.setChecked(self._get_default_value(param_id))
            widget.setToolTip(display_name)
            
        else:
            # 默认文本输入
            widget = QLineEdit()
            widget.setText(str(self._get_default_value(param_id)))
            widget.setToolTip(display_name)
            
        return widget

    def _get_default_value(self, param_id):
        """获取参数默认值"""
        defaults = {
            "CN": 70.0,
            "Ia_coefficient": 0.2,
            "dx": 100.0,
            "dt": 1.0,
            "nx": 100,
            "nt": 1000,
            "manning_n": 0.015,
            "channel_width": 10.0,
            "channel_slope": 0.001,
            "channel_shape": "矩形",
            "side_slope": 2.0,
            "parabola_coefficient": 0.1,
            "radius": 5.0,
            "lateral_inflow": 0.0,
            "lateral_outflow": 0.0,
            "wind_speed": 0.0,
            "wind_direction": 0.0,
            "water_temperature": 20.0,
            "land_use": "行作物",
            "soil_type": "C",
            "vegetation_cover": 0.5,
            "slope": 5.0,
            "antecedent_days": 5.0,
            "auto_calculate_antecedent": True,
            "antecedent_rainfall": 15.0,
            "temperature": 20.0,
            "evaporation": 2.0
        }
        return defaults.get(param_id, 0.0)

    def _get_unit_suffix(self, param_id):
        """获取参数单位后缀"""
        units = {
            "CN": "",
            "Ia_coefficient": "",
            "dx": " m",
            "dt": " s",
            "nx": "",
            "nt": "",
            "manning_n": "",
            "channel_width": " m",
            "channel_slope": "",
            "side_slope": "",
            "parabola_coefficient": "",
            "radius": " m",
            "lateral_inflow": " m³/s/m",
            "lateral_outflow": " m³/s/m",
            "wind_speed": " m/s",
            "wind_direction": "°",
            "water_temperature": "°C",
            "vegetation_cover": "",
            "slope": "%",
            "antecedent_days": " 天",
            "antecedent_rainfall": " mm",
            "temperature": "°C",
            "evaporation": " mm"
        }
        return units.get(param_id, "")

    def _get_category_display_name(self, category_name):
        """获取分类显示名称"""
        names = {
            "basic": "基本参数",
            "land_use": "土地利用参数",
            "climate": "气候参数",
            "channel_shape": "渠道形状参数",
            "environmental": "环境参数"
        }
        return names.get(category_name, category_name)

    def get_params(self):
        """从UI控件中收集所有参数值。"""
        params = {}
        for param_id, widget in self.param_widgets.items():
            try:
                if isinstance(widget, QDoubleSpinBox):
                    params[param_id] = widget.value()
                elif isinstance(widget, QSpinBox):
                    params[param_id] = widget.value()
                elif isinstance(widget, QComboBox):
                    params[param_id] = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    params[param_id] = widget.isChecked()
                elif isinstance(widget, QLineEdit):
                    # 尝试将参数转换为浮点数
                    params[param_id] = float(widget.text())
                else:
                    params[param_id] = widget.text()
            except (ValueError, TypeError):
                print(f"警告：参数 '{param_id}' 的值不是有效的数字，将忽略。")
                params[param_id] = None
        return params
