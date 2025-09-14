from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QTabWidget,
    QScrollArea,
    QGridLayout,
    QTextEdit,
)
from PyQt6.QtCore import pyqtSignal

from .icon_utils import load_icon


class ScheduleTab(QWidget):
    """'调度优化' 选项卡 UI - 完整的NSGA-III参数配置。"""

    # 发射信号在未来可用，如需要让外部捕获运行事件。
    run_schedule_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # -------------------- 优化目标 --------------------
        objectives_group = QGroupBox("优化目标 (至少选择一个)")
        obj_layout = QVBoxLayout()
        self.chk_flood = QCheckBox("防洪  —  最小化最大下泄流量")
        self.chk_power = QCheckBox("发电  —  最大化发电量")
        self.chk_supply = QCheckBox("供水  —  满足下游需水量")
        self.chk_ecology = QCheckBox("生态  —  维持生态基流")
        # 默认全部启用
        for chk in (self.chk_flood, self.chk_power, self.chk_supply, self.chk_ecology):
            chk.setChecked(True)
            obj_layout.addWidget(chk)
        objectives_group.setLayout(obj_layout)
        scroll_layout.addWidget(objectives_group)

        # -------------------- 水库物理参数 --------------------
        reservoir_group = QGroupBox("水库物理参数")
        reservoir_layout = QFormLayout()
        
        # 流量约束参数
        self.le_q_min = QDoubleSpinBox()
        self.le_q_min.setRange(0, 10000)
        self.le_q_min.setValue(0.0)
        self.le_q_min.setSuffix(" m³/s")
        self.le_q_min.setToolTip("最小下泄流量")
        
        self.le_q_max = QDoubleSpinBox()
        self.le_q_max.setRange(0, 10000)
        self.le_q_max.setValue(1000.0)
        self.le_q_max.setSuffix(" m³/s")
        self.le_q_max.setToolTip("最大下泄流量")
        
        self.le_q_allowed = QDoubleSpinBox()
        self.le_q_allowed.setRange(0, 10000)
        self.le_q_allowed.setValue(800.0)
        self.le_q_allowed.setSuffix(" m³/s")
        self.le_q_allowed.setToolTip("防洪允许的最大下泄流量")
        
        self.le_q_target = QDoubleSpinBox()
        self.le_q_target.setRange(0, 10000)
        self.le_q_target.setValue(500.0)
        self.le_q_target.setSuffix(" m³/s")
        self.le_q_target.setToolTip("下游供水目标流量")
        
        self.le_q_eco = QDoubleSpinBox()
        self.le_q_eco.setRange(0, 10000)
        self.le_q_eco.setValue(50.0)
        self.le_q_eco.setSuffix(" m³/s")
        self.le_q_eco.setToolTip("生态基流要求")
        
        # 水头参数
        self.le_head = QDoubleSpinBox()
        self.le_head.setRange(0, 500)
        self.le_head.setValue(50.0)
        self.le_head.setSuffix(" m")
        self.le_head.setToolTip("发电水头")
        
        # 调度时间范围
        self.le_horizon = QSpinBox()
        self.le_horizon.setRange(1, 168)  # 1小时到1周
        self.le_horizon.setValue(24)
        self.le_horizon.setSuffix(" 小时")
        self.le_horizon.setToolTip("调度时间步长数")
        
        reservoir_layout.addRow("最小下泄流量:", self.le_q_min)
        reservoir_layout.addRow("最大下泄流量:", self.le_q_max)
        reservoir_layout.addRow("防洪允许流量:", self.le_q_allowed)
        reservoir_layout.addRow("供水目标流量:", self.le_q_target)
        reservoir_layout.addRow("生态基流:", self.le_q_eco)
        reservoir_layout.addRow("发电水头:", self.le_head)
        reservoir_layout.addRow("调度时间范围:", self.le_horizon)
        reservoir_group.setLayout(reservoir_layout)
        scroll_layout.addWidget(reservoir_group)

        # -------------------- 发电效率参数 --------------------
        power_group = QGroupBox("发电效率参数")
        power_layout = QFormLayout()
        
        self.le_power_efficiency = QDoubleSpinBox()
        self.le_power_efficiency.setRange(0.1, 1.0)
        self.le_power_efficiency.setValue(0.85)
        self.le_power_efficiency.setDecimals(3)
        self.le_power_efficiency.setSuffix("")
        self.le_power_efficiency.setToolTip("发电效率系数")
        
        self.le_power_coefficient = QDoubleSpinBox()
        self.le_power_coefficient.setRange(0.1, 10.0)
        self.le_power_coefficient.setValue(9.81)
        self.le_power_coefficient.setDecimals(3)
        self.le_power_coefficient.setSuffix("")
        self.le_power_coefficient.setToolTip("发电系数 (ρg)")
        
        self.le_min_power_output = QDoubleSpinBox()
        self.le_min_power_output.setRange(0, 1000)
        self.le_min_power_output.setValue(10.0)
        self.le_min_power_output.setSuffix(" MW")
        self.le_min_power_output.setToolTip("最小发电出力")
        
        self.le_max_power_output = QDoubleSpinBox()
        self.le_max_power_output.setRange(0, 10000)
        self.le_max_power_output.setValue(500.0)
        self.le_max_power_output.setSuffix(" MW")
        self.le_max_power_output.setToolTip("最大发电出力")
        
        power_layout.addRow("发电效率:", self.le_power_efficiency)
        power_layout.addRow("发电系数:", self.le_power_coefficient)
        power_layout.addRow("最小出力:", self.le_min_power_output)
        power_layout.addRow("最大出力:", self.le_max_power_output)
        power_group.setLayout(power_layout)
        scroll_layout.addWidget(power_group)

        # -------------------- 供水优先级参数 --------------------
        supply_group = QGroupBox("供水优先级参数")
        supply_layout = QFormLayout()
        
        self.le_supply_priority = QComboBox()
        self.le_supply_priority.addItems(["高", "中", "低"])
        self.le_supply_priority.setCurrentText("中")
        self.le_supply_priority.setToolTip("供水优先级")
        
        self.le_supply_reliability = QDoubleSpinBox()
        self.le_supply_reliability.setRange(0.5, 1.0)
        self.le_supply_reliability.setValue(0.95)
        self.le_supply_reliability.setDecimals(3)
        self.le_supply_reliability.setSuffix("")
        self.le_supply_reliability.setToolTip("供水可靠性要求")
        
        self.le_supply_penalty = QDoubleSpinBox()
        self.le_supply_penalty.setRange(1, 100)
        self.le_supply_penalty.setValue(10.0)
        self.le_supply_penalty.setSuffix("")
        self.le_supply_penalty.setToolTip("供水缺口惩罚系数")
        
        supply_layout.addRow("供水优先级:", self.le_supply_priority)
        supply_layout.addRow("供水可靠性:", self.le_supply_reliability)
        supply_layout.addRow("缺口惩罚系数:", self.le_supply_penalty)
        supply_group.setLayout(supply_layout)
        scroll_layout.addWidget(supply_group)

        # -------------------- 生态约束参数 --------------------
        ecology_group = QGroupBox("生态约束参数")
        ecology_layout = QFormLayout()
        
        self.le_eco_priority = QComboBox()
        self.le_eco_priority.addItems(["高", "中", "低"])
        self.le_eco_priority.setCurrentText("中")
        self.le_eco_priority.setToolTip("生态保护优先级")
        
        self.le_eco_penalty = QDoubleSpinBox()
        self.le_eco_penalty.setRange(1, 100)
        self.le_eco_penalty.setValue(5.0)
        self.le_eco_penalty.setSuffix("")
        self.le_eco_penalty.setToolTip("生态基流不满足惩罚系数")
        
        self.le_eco_duration = QSpinBox()
        self.le_eco_duration.setRange(1, 24)
        self.le_eco_duration.setValue(4)
        self.le_eco_duration.setSuffix(" 小时")
        self.le_eco_duration.setToolTip("生态基流最小持续时间")
        
        ecology_layout.addRow("生态优先级:", self.le_eco_priority)
        ecology_layout.addRow("生态惩罚系数:", self.le_eco_penalty)
        ecology_layout.addRow("最小持续时间:", self.le_eco_duration)
        ecology_group.setLayout(ecology_layout)
        scroll_layout.addWidget(ecology_group)

        # -------------------- 算法参数 --------------------
        algorithm_group = QGroupBox("NSGA-III算法参数")
        algorithm_layout = QFormLayout()
        
        self.le_population_size = QSpinBox()
        self.le_population_size.setRange(10, 1000)
        self.le_population_size.setValue(100)
        self.le_population_size.setToolTip("种群大小")
        
        self.le_iterations = QSpinBox()
        self.le_iterations.setRange(10, 1000)
        self.le_iterations.setValue(100)
        self.le_iterations.setToolTip("迭代次数")
        
        self.le_reference_points = QSpinBox()
        self.le_reference_points.setRange(4, 100)
        self.le_reference_points.setValue(12)
        self.le_reference_points.setToolTip("参考点数量")
        
        self.le_crossover_prob = QDoubleSpinBox()
        self.le_crossover_prob.setRange(0.1, 1.0)
        self.le_crossover_prob.setValue(0.9)
        self.le_crossover_prob.setDecimals(3)
        self.le_crossover_prob.setToolTip("交叉概率")
        
        self.le_mutation_prob = QDoubleSpinBox()
        self.le_mutation_prob.setRange(0.01, 0.5)
        self.le_mutation_prob.setValue(0.1)
        self.le_mutation_prob.setDecimals(3)
        self.le_mutation_prob.setToolTip("变异概率")
        
        algorithm_layout.addRow("种群大小:", self.le_population_size)
        algorithm_layout.addRow("迭代次数:", self.le_iterations)
        algorithm_layout.addRow("参考点数量:", self.le_reference_points)
        algorithm_layout.addRow("交叉概率:", self.le_crossover_prob)
        algorithm_layout.addRow("变异概率:", self.le_mutation_prob)
        algorithm_group.setLayout(algorithm_layout)
        scroll_layout.addWidget(algorithm_group)

        # -------------------- 权重配置 --------------------
        weights_group = QGroupBox("目标权重配置")
        weights_layout = QFormLayout()
        
        self.le_flood_weight = QDoubleSpinBox()
        self.le_flood_weight.setRange(0, 1)
        self.le_flood_weight.setValue(0.25)
        self.le_flood_weight.setDecimals(3)
        self.le_flood_weight.setToolTip("防洪目标权重")
        
        self.le_power_weight = QDoubleSpinBox()
        self.le_power_weight.setRange(0, 1)
        self.le_power_weight.setValue(0.25)
        self.le_power_weight.setDecimals(3)
        self.le_power_weight.setToolTip("发电目标权重")
        
        self.le_supply_weight = QDoubleSpinBox()
        self.le_supply_weight.setRange(0, 1)
        self.le_supply_weight.setValue(0.25)
        self.le_supply_weight.setDecimals(3)
        self.le_supply_weight.setToolTip("供水目标权重")
        
        self.le_ecology_weight = QDoubleSpinBox()
        self.le_ecology_weight.setRange(0, 1)
        self.le_ecology_weight.setValue(0.25)
        self.le_ecology_weight.setDecimals(3)
        self.le_ecology_weight.setToolTip("生态目标权重")
        
        weights_layout.addRow("防洪权重:", self.le_flood_weight)
        weights_layout.addRow("发电权重:", self.le_power_weight)
        weights_layout.addRow("供水权重:", self.le_supply_weight)
        weights_layout.addRow("生态权重:", self.le_ecology_weight)
        weights_group.setLayout(weights_layout)
        scroll_layout.addWidget(weights_group)

        # 设置滚动区域
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # -------------------- 运行按钮 --------------------
        self.run_button = QPushButton("运行调度优化")
        self.run_button.setIcon(load_icon("run.png", "media-playback-start"))
        self.run_button.clicked.connect(self.run_schedule_requested)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # 公共接口：获取用户输入
    # ------------------------------------------------------------------
    def get_objectives(self) -> dict[str, bool]:
        """返回用户勾选的目标字典。"""
        return {
            "flood": self.chk_flood.isChecked(),
            "power": self.chk_power.isChecked(),
            "supply": self.chk_supply.isChecked(),
            "ecology": self.chk_ecology.isChecked(),
        }

    def get_reservoir_params(self) -> dict[str, float]:
        """获取水库物理参数。"""
        return {
            "Q_min": self.le_q_min.value(),
            "Q_max": self.le_q_max.value(),
            "Q_allowed": self.le_q_allowed.value(),
            "Q_target": self.le_q_target.value(),
            "Q_eco": self.le_q_eco.value(),
            "head": self.le_head.value(),
            "horizon": self.le_horizon.value(),
        }

    def get_power_params(self) -> dict[str, float]:
        """获取发电效率参数。"""
        return {
            "power_efficiency": self.le_power_efficiency.value(),
            "power_coefficient": self.le_power_coefficient.value(),
            "min_power_output": self.le_min_power_output.value(),
            "max_power_output": self.le_max_power_output.value(),
        }

    def get_supply_params(self) -> dict[str, str | float]:
        """获取供水参数。"""
        return {
            "supply_priority": self.le_supply_priority.currentText(),
            "supply_reliability": self.le_supply_reliability.value(),
            "supply_penalty": self.le_supply_penalty.value(),
        }

    def get_ecology_params(self) -> dict[str, str | float | int]:
        """获取生态约束参数。"""
        return {
            "ecology_priority": self.le_eco_priority.currentText(),
            "ecology_penalty": self.le_eco_penalty.value(),
            "ecology_duration": self.le_eco_duration.value(),
        }

    def get_algorithm_params(self) -> dict[str, float | int]:
        """从控件读取算法参数。"""
        return {
            "population_size": self.le_population_size.value(),
            "iterations": self.le_iterations.value(),
            "reference_points": self.le_reference_points.value(),
            "crossover_prob": self.le_crossover_prob.value(),
            "mutation_prob": self.le_mutation_prob.value(),
        }

    def get_weight_params(self) -> dict[str, float]:
        """获取目标权重参数。"""
        return {
            "flood_weight": self.le_flood_weight.value(),
            "power_weight": self.le_power_weight.value(),
            "supply_weight": self.le_supply_weight.value(),
            "ecology_weight": self.le_ecology_weight.value(),
        }

    def get_all_params(self) -> dict[str, str | float | int]:
        """获取所有参数的综合字典。"""
        params = {}
        params.update(self.get_reservoir_params())
        params.update(self.get_power_params())
        params.update(self.get_supply_params())
        params.update(self.get_ecology_params())
        params.update(self.get_algorithm_params())
        params.update(self.get_weight_params())
        return params