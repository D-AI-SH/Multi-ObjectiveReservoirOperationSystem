import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt

class SaintVenantModel:
    """
    Saint-Venant水动力模型完整实现
    基于一维明渠非恒定流的基本方程，包含多种渠道形状和边界条件
    """
    
    # 渠道形状类型
    CHANNEL_SHAPES = {
        "矩形": "rectangular",
        "梯形": "trapezoidal", 
        "三角形": "triangular",
        "抛物线形": "parabolic",
        "圆形": "circular"
    }
    
    # 边界条件类型
    BOUNDARY_TYPES = {
        "上游流量": "upstream_discharge",
        "上游水位": "upstream_stage",
        "下游水位": "downstream_stage", 
        "下游流量": "downstream_discharge",
        "水位流量关系": "rating_curve"
    }
    
    def __init__(self):
        """
        初始化Saint-Venant模型
        """
        # 物理常数（将在set_parameters中从参数文件加载）
        # 这些是临时默认值，会被set_parameters中的参数覆盖
        self.g = None  # 重力加速度 (m/s²)
        self.water_density = None  # 水的密度 (kg/m³)
        self.air_density = None  # 空气密度 (kg/m³)
        self.kinematic_viscosity = None  # 运动粘性系数 (m²/s)
        self.reference_temperature = None  # 参考温度 (℃)
        self.thermal_expansion = None  # 热膨胀系数 (1/℃)
        self.wind_drag_coefficient = None  # 风阻力系数
        
        # 模型参数
        self.dx = None  # 空间步长 (m)
        self.dt = None  # 时间步长 (s)
        self.nx = None  # 空间网格数
        self.nt = None  # 时间网格数
        self.manning_n = None  # Manning粗糙系数
        self.channel_width = None  # 渠道宽度 (m)
        self.channel_slope = None  # 渠道坡度
        self.channel_shape = None  # 渠道形状
        self.channel_params = {}  # 渠道形状参数
        
        # 侧向入流参数
        self.lateral_inflow = None  # 侧向入流 (m³/s/m)
        self.lateral_outflow = None  # 侧向出流 (m³/s/m)
        
        # 风应力参数
        self.wind_speed = None  # 风速 (m/s)
        self.wind_direction = None  # 风向 (度)
        
        # 温度影响参数
        self.water_temperature = None  # 水温 (℃)
        
        # 计算结果存储
        self.water_depth = None  # 水深 (m)
        self.velocity = None  # 流速 (m/s)
        self.discharge = None  # 流量 (m³/s)
        self.water_surface_elevation = None  # 水面高程 (m)
        self.time_points = None  # 时间点
        self.space_points = None  # 空间点
        
    def set_parameters(self, params: Dict):
        """
        设置模型参数
        
        :param params: 参数字典，包含：
            - basic: 基本参数
            - physical_constants: 物理常数
            - boundary_conditions: 边界条件
            - numerical_parameters: 数值参数
        """
        # 基本参数
        basic_params = params.get('basic', {})
        self.dx = basic_params.get('dx', 100.0)
        self.dt = basic_params.get('dt', 1.0)
        self.nx = int(basic_params.get('nx', 100))
        self.nt = int(basic_params.get('nt', 1000))
        self.manning_n = basic_params.get('manning_n', 0.015)
        self.channel_width = basic_params.get('channel_width', 10.0)
        self.channel_slope = basic_params.get('channel_slope', 0.001)
        self.channel_shape = basic_params.get('channel_shape', '矩形')
        self.channel_params = basic_params.get('channel_params', {})
        
        # 物理常数
        physical_constants = params.get('physical_constants', {})
        self.g = physical_constants.get('gravity', 9.81)
        self.water_density = physical_constants.get('water_density', 1000.0)
        self.air_density = physical_constants.get('air_density', 1.225)
        self.kinematic_viscosity = physical_constants.get('kinematic_viscosity', 1e-6)
        self.reference_temperature = physical_constants.get('reference_temperature', 20.0)
        self.thermal_expansion = physical_constants.get('thermal_expansion_coefficient', 2.1e-4)
        self.wind_drag_coefficient = physical_constants.get('wind_drag_coefficient', 0.0013)
        
        # 边界条件参数
        boundary_conditions = params.get('boundary_conditions', {})
        self.wind_speed = boundary_conditions.get('wind_speed', 0.0)
        self.wind_direction = boundary_conditions.get('wind_direction', 0.0)
        self.water_temperature = boundary_conditions.get('water_temperature', 20.0)
        
        # 数值参数
        numerical_parameters = params.get('numerical_parameters', {})
        self._numerical_params = numerical_parameters
        
        # 侧向流参数（保持向后兼容）
        self.lateral_inflow = params.get('lateral_inflow', 0.0)
        self.lateral_outflow = params.get('lateral_outflow', 0.0)
        
    def set_boundary_conditions(self, upstream_condition: np.ndarray, 
                               downstream_condition: np.ndarray,
                               boundary_type: str = "upstream_discharge"):
        """
        设置边界条件
        
        :param upstream_condition: 上游边界条件时间序列
        :param downstream_condition: 下游边界条件时间序列
        :param boundary_type: 边界条件类型
        """
        # 统一为 numpy 数组
        self.upstream_condition = np.asarray(upstream_condition, dtype=float)
        self.downstream_condition = np.asarray(downstream_condition, dtype=float)
        self.boundary_type = boundary_type
        
    def set_initial_conditions(self, initial_depth: np.ndarray, 
                              initial_velocity: np.ndarray):
        """
        设置初始条件
        
        :param initial_depth: 初始水深分布 (m)
        :param initial_velocity: 初始流速分布 (m/s)
        """
        if len(initial_depth) != self.nx:
            raise ValueError(f"初始水深长度必须为 {self.nx}")
        if len(initial_velocity) != self.nx:
            raise ValueError(f"初始流速长度必须为 {self.nx}")
            
        # 统一为 numpy 数组
        self.initial_depth = np.asarray(initial_depth, dtype=float)
        self.initial_velocity = np.asarray(initial_velocity, dtype=float)
        
    def calculate_channel_properties(self, depth: float) -> Dict[str, float]:
        """
        根据渠道形状计算水力特性
        
        :param depth: 水深 (m)
        :return: 包含面积、湿周、水力半径等的字典
        """
        if self.channel_width is None:
            raise ValueError("渠道宽度未设置")
            
        if self.channel_shape == "矩形":
            area = self.channel_width * depth
            perimeter = self.channel_width + 2 * depth
            hydraulic_radius = area / perimeter
            top_width = self.channel_width
            
        elif self.channel_shape == "梯形":
            side_slope = float(self.channel_params.get('side_slope', 2.0))
            area = depth * (self.channel_width + side_slope * depth)
            perimeter = self.channel_width + 2 * depth * np.sqrt(1 + side_slope**2)
            hydraulic_radius = area / perimeter
            top_width = self.channel_width + 2 * side_slope * depth
            
        elif self.channel_shape == "三角形":
            side_slope = float(self.channel_params.get('side_slope', 1.0))
            area = side_slope * depth**2
            perimeter = 2 * depth * np.sqrt(1 + side_slope**2)
            hydraulic_radius = area / perimeter
            top_width = 2 * side_slope * depth
            
        elif self.channel_shape == "抛物线形":
            # 抛物线形渠道: y = ax²
            a = float(self.channel_params.get('parabola_coefficient', 0.1))
            area = (2/3) * np.sqrt(depth/a) * depth
            perimeter = 2 * np.sqrt(depth/a) * (1 + (2*a*depth)**2/3)
            hydraulic_radius = area / perimeter
            top_width = 2 * np.sqrt(depth/a)
            
        elif self.channel_shape == "圆形":
            radius = float(self.channel_params.get('radius', self.channel_width/2))
            if depth > 2 * radius:
                raise ValueError("水深不能超过直径")
            
            # 计算圆形渠道的水力特性
            theta = 2 * np.arccos((radius - depth) / radius)
            area = radius**2 * (theta - np.sin(theta)) / 2
            perimeter = radius * theta
            hydraulic_radius = area / perimeter
            top_width = 2 * radius * np.sin(theta/2)
            
        else:
            # 默认矩形
            area = self.channel_width * depth
            perimeter = self.channel_width + 2 * depth
            hydraulic_radius = area / perimeter
            top_width = self.channel_width
            
        return {
            'area': float(area),
            'perimeter': float(perimeter),
            'hydraulic_radius': float(hydraulic_radius),
            'top_width': float(top_width)
        }
    
    def _calculate_hydraulic_properties(self, depth: float) -> Tuple[float, float]:
        """
        兼容旧调用：返回 (面积, 湿周)
        """
        props = self.calculate_channel_properties(depth)
        return props['area'], props['perimeter']
        
    def calculate_manning_velocity(self, depth: float, slope: float) -> float:
        """
        使用Manning公式计算流速
        
        :param depth: 水深 (m)
        :param slope: 水力坡度
        :return: 流速 (m/s)
        """
        if depth <= 0 or self.manning_n is None:
            return 0.0
            
        # 获取渠道水力特性
        props = self.calculate_channel_properties(depth)
        hydraulic_radius = props['hydraulic_radius']
        
        # Manning公式: v = (1/n) * R^(2/3) * S^(1/2)
        velocity = (1.0 / self.manning_n) * (hydraulic_radius ** (2.0/3.0)) * (slope ** 0.5)
        return velocity
        
    def calculate_wind_stress(self, depth: float) -> float:
        """
        计算风应力对水流的影响
        
        :param depth: 水深 (m)
        :return: 风应力 (m/s²)
        """
        if (self.wind_speed is None or self.wind_speed <= 0 or 
            self.wind_direction is None or depth <= 0):
            return 0.0
            
        # 风应力公式: τ = ρ_air * C_d * U_w² / (ρ_water * h)
        wind_stress = (self.air_density * self.wind_drag_coefficient * 
                      self.wind_speed**2) / (self.water_density * depth)
        
        # 考虑风向影响
        wind_angle_rad = np.radians(self.wind_direction)
        wind_stress_x = wind_stress * np.cos(wind_angle_rad)
        
        return wind_stress_x
        
    def calculate_temperature_effects(self, depth: float, velocity: float) -> float:
        """
        计算温度对水流的影响
        
        :param depth: 水深 (m)
        :param velocity: 流速 (m/s)
        :return: 温度修正系数
        """
        if self.water_temperature is None:
            return 1.0
            
        # 温度对水密度的影响
        temp_factor = 1.0 + self.thermal_expansion * (self.water_temperature - self.reference_temperature)
        
        # 温度对粘性的影响（简化处理）
        viscosity_factor = 1.0 + 0.02 * (self.water_temperature - self.reference_temperature)
        
        return temp_factor / viscosity_factor
        
    def solve_saint_venant(self):
        """
        求解Saint-Venant方程组
        使用有限差分方法（Lax-Wendroff格式）
        """
        if not all([self.dx, self.dt, self.nx, self.nt, 
                   hasattr(self, 'initial_depth'), 
                   hasattr(self, 'initial_velocity')]):
            raise ValueError("请先设置所有必要的参数和初始条件")
        # 强制断言，便于类型收窄
        assert self.dx is not None and self.dt is not None and self.nx is not None and self.nt is not None
        assert self.channel_width is not None and self.channel_slope is not None
        # 使用局部变量，避免 Optional 类型带来的静态类型告警
        dx: float = float(self.dx)
        dt: float = float(self.dt)
        nx: int = int(self.nx)
        nt: int = int(self.nt)
        channel_width: float = float(self.channel_width)
        channel_slope: float = float(self.channel_slope)
            
        # 检查CFL条件
        max_velocity = np.max(self.initial_velocity) + np.sqrt(self.g * np.max(self.initial_depth))
        cfl = max_velocity * dt / dx
        if cfl > 1.0:
            print(f"警告：CFL数 = {cfl:.3f} > 1.0，可能不稳定")
            
        # 初始化数组
        self.water_depth = np.zeros((nt, nx))
        self.velocity = np.zeros((nt, nx))
        self.discharge = np.zeros((nt, nx))
        self.water_surface_elevation = np.zeros((nt, nx))
        
        # 设置初始条件
        self.water_depth[0, :] = self.initial_depth
        self.velocity[0, :] = self.initial_velocity
        
        # 计算初始流量和水面高程
        for i in range(nx):
            props = self.calculate_channel_properties(self.water_depth[0, i])
            self.discharge[0, i] = props['area'] * self.velocity[0, i]
            self.water_surface_elevation[0, i] = i * dx * channel_slope + self.water_depth[0, i]
        
        # 初始化诊断信息
        self._diagnostics = {
            'cfl': float(cfl) if cfl is not None else None,
            'first_invalid': None,   # (t_idx, x_idx, depth, velocity)
            'warnings': []
        }
        
        # 时间步进求解
        for n in range(nt - 1):
            for i in range(1, nx - 1):
                # 获取当前水力特性
                current_depth = max(self.water_depth[n, i], 0.01)
                props = self.calculate_channel_properties(current_depth)
                
                # 连续性方程: ∂A/∂t + ∂Q/∂x = q_l
                # 动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x = gA(S0 - Sf) + 风应力 + 侧向流动量
                
                # 计算空间导数
                depth_gradient = (self.water_depth[n, i+1] - self.water_depth[n, i-1]) / (2 * dx)
                velocity_gradient = (self.velocity[n, i+1] - self.velocity[n, i-1]) / (2 * dx)
                
                # 计算摩擦坡度
                current_velocity = self.velocity[n, i]
                friction_slope = (self.manning_n ** 2 * current_velocity ** 2) / (props['hydraulic_radius'] ** (4.0/3.0))
                
                # 计算风应力
                wind_stress = self.calculate_wind_stress(current_depth)
                
                # 计算温度影响
                temp_factor = self.calculate_temperature_effects(current_depth, current_velocity)
                
                # 连续性方程更新（添加数值保护）
                lateral_flow = self.lateral_inflow - self.lateral_outflow
                
                # 限制梯度大小，防止数值不稳定
                depth_gradient = np.clip(depth_gradient, -10.0, 10.0)
                velocity_gradient = np.clip(velocity_gradient, -10.0, 10.0)
                
                depth_update = (self.water_depth[n, i] - 
                    dt * (current_velocity * depth_gradient + 
                              current_depth * velocity_gradient) +
                    dt * lateral_flow / props['top_width'])
                
                # 获取数值限制参数
                numerical_params = getattr(self, '_numerical_params', {})
                max_depth_limit = numerical_params.get('max_depth_limit', 100.0)
                min_depth_limit = numerical_params.get('min_depth_limit', 0.001)
                max_velocity_limit = numerical_params.get('max_velocity_limit', 50.0)
                min_velocity_limit = numerical_params.get('min_velocity_limit', -50.0)
                
                # 确保水深非负且有限，并限制最大值
                self.water_depth[n+1, i] = np.clip(depth_update, min_depth_limit, max_depth_limit) if np.isfinite(depth_update) else min_depth_limit
                
                # 动量方程更新（添加数值保护）
                velocity_update = (current_velocity - 
                    dt * (current_velocity * velocity_gradient + 
                              self.g * depth_gradient - 
                              self.g * (channel_slope - friction_slope) +
                              wind_stress))
                
                # 应用温度修正并确保流速有限，限制最大值
                final_velocity = velocity_update * temp_factor
                self.velocity[n+1, i] = np.clip(final_velocity, min_velocity_limit, max_velocity_limit) if np.isfinite(final_velocity) else 0.0
                
                # 更新流量和水面高程
                new_depth = max(self.water_depth[n+1, i], 0.01)
                new_props = self.calculate_channel_properties(new_depth)
                self.discharge[n+1, i] = new_props['area'] * self.velocity[n+1, i]
                self.water_surface_elevation[n+1, i] = (i * dx * channel_slope + new_depth)
                
                # 基本的数值稳定性检查（仅记录，不中断）
                if not (np.isfinite(self.water_depth[n+1, i]) and np.isfinite(self.velocity[n+1, i])):
                    if self._diagnostics.get('first_invalid') is None:
                        self._diagnostics['first_invalid'] = {
                            'time_index': int(n+1),
                            'space_index': int(i),
                            'depth_value': float(self.water_depth[n+1, i]) if np.isfinite(self.water_depth[n+1, i]) else 'NaN/Inf',
                            'velocity_value': float(self.velocity[n+1, i]) if np.isfinite(self.velocity[n+1, i]) else 'NaN/Inf'
                        }
                        print(f"警告：发现非有限数值，t={n+1}, i={i}")
            
            # 边界条件处理
            self._apply_boundary_conditions(n)
        
        # 生成时间和空间点
        self.time_points = np.arange(nt) * dt
        self.space_points = np.arange(nx) * dx
        
    def _apply_boundary_conditions(self, n: int):
        """应用边界条件"""
        if n >= len(self.upstream_condition) - 1:
            return
            
        if self.boundary_type == "upstream_discharge":
            # 上游边界：给定流量
            upstream_discharge = float(self.upstream_condition[n])
            # 使用特征线法或简化方法计算上游水深
            if n > 0:
                # 简单外推
                self.water_depth[n+1, 0] = self.water_depth[n, 1]
                self.velocity[n+1, 0] = upstream_discharge / (self.channel_width * self.water_depth[n+1, 0])
            else:
                # 初始条件
                self.water_depth[n+1, 0] = self.initial_depth[0]
                self.velocity[n+1, 0] = upstream_discharge / (self.channel_width * self.water_depth[n+1, 0])
                
            self.discharge[n+1, 0] = upstream_discharge
            
        elif self.boundary_type == "upstream_stage":
            # 上游边界：给定水位
            upstream_stage = float(self.upstream_condition[n])
            self.water_depth[n+1, 0] = upstream_stage
            # 使用特征线法计算流速
            self.velocity[n+1, 0] = self.velocity[n, 1]  # 简单外推
            props = self.calculate_channel_properties(self.water_depth[n+1, 0])
            self.discharge[n+1, 0] = props['area'] * self.velocity[n+1, 0]
            
        # 下游边界处理
        if n < len(self.downstream_condition) - 1:
            if self.boundary_type in ["downstream_stage", "downstream_discharge"]:
                downstream_condition = float(self.downstream_condition[n])
                if self.boundary_type == "downstream_stage":
                    self.water_depth[n+1, -1] = downstream_condition
                else:
                    # 给定流量，需要反算水深
                    self.discharge[n+1, -1] = downstream_condition
                    # 简化处理，使用上一时刻的水深
                    self.water_depth[n+1, -1] = self.water_depth[n, -1]
                    
                self.velocity[n+1, -1] = self.velocity[n, -2]  # 简单外推
                props = self.calculate_channel_properties(self.water_depth[n+1, -1])
                self.discharge[n+1, -1] = props['area'] * self.velocity[n+1, -1]

    def run(self, input_data: pd.DataFrame, params: Dict) -> Dict:
        """
        运行Saint-Venant模型
        
        :param input_data: 输入数据，包含：
            - upstream_discharge: 上游流量时间序列
            - downstream_depth: 下游水深时间序列
            - initial_depth: 初始水深分布
            - initial_velocity: 初始流速分布
            - lateral_inflow: 侧向入流时间序列（可选）
            - wind_speed: 风速时间序列（可选）
            - water_temperature: 水温时间序列（可选）
        :param params: 模型参数字典
        :return: 包含结果的字典
        """
        try:
            import warnings
            # 设置参数
            self.set_parameters(params)
            
            # 从输入数据提取边界条件和初始条件
            # 使用参数中的默认值
            default_upstream = params.get('default_values', {}).get('default_upstream_discharge', 4.5)
            default_downstream = params.get('default_values', {}).get('default_downstream_depth', 1.2)
            default_initial_depth = params.get('default_values', {}).get('default_initial_depth', 1.0)
            default_initial_velocity = params.get('default_values', {}).get('default_initial_velocity', 0.5)
            
            upstream_condition = input_data.get('upstream_discharge', 
                                              np.ones(self.nt) * default_upstream)
            downstream_condition = input_data.get('downstream_depth', 
                                                np.ones(self.nt) * default_downstream)
            
            # 设置初始条件（如果没有提供，使用均匀分布）
            if 'initial_depth' in input_data:
                initial_depth = input_data['initial_depth']
            else:
                initial_depth = np.ones(self.nx) * default_initial_depth
                
            if 'initial_velocity' in input_data:
                initial_velocity = input_data['initial_velocity']
            else:
                initial_velocity = np.ones(self.nx) * default_initial_velocity
            
            # 设置边界和初始条件
            self.set_boundary_conditions(upstream_condition, downstream_condition)
            self.set_initial_conditions(initial_depth, initial_velocity)
            
            # 求解方程（捕获数值警告）
            with warnings.catch_warnings(record=True) as wlist:
                warnings.simplefilter('always', category=RuntimeWarning)
                old_err = np.seterr(all='warn')
                try:
                    self.solve_saint_venant()
                finally:
                    np.seterr(**old_err)
                # 确保诊断字典存在
                if not hasattr(self, '_diagnostics'):
                    self._diagnostics = {'cfl': None, 'first_invalid': None, 'warnings': []}
                # 记录运行期间的数值警告
                self._diagnostics['warnings'] = [str(w.message) for w in wlist if isinstance(w.message, RuntimeWarning)]
            
            # 计算水力特性
            hydraulic_radius = np.zeros_like(self.water_depth)
            wetted_perimeter = np.zeros_like(self.water_depth)
            flow_area = np.zeros_like(self.water_depth)
            froude_number = np.zeros_like(self.water_depth)
            reynolds_number = np.zeros_like(self.water_depth)
            shear_stress = np.zeros_like(self.water_depth)
            
            for i in range(self.nt):
                for j in range(self.nx):
                    depth = self.water_depth[i, j]
                    if depth > 0:
                        # 计算水力特性
                        area, perimeter = self._calculate_hydraulic_properties(depth)
                        if area is not None and perimeter is not None:
                            flow_area[i, j] = area
                            wetted_perimeter[i, j] = perimeter
                            hydraulic_radius[i, j] = area / perimeter if perimeter > 0 else 0
                            
                            # 计算弗劳德数
                            velocity = self.velocity[i, j]
                            if velocity is not None:
                                froude_number[i, j] = velocity / np.sqrt(self.g * depth) if depth > 0 else 0
                                
                                # 计算雷诺数
                                reynolds_number[i, j] = velocity * depth / self.kinematic_viscosity if depth > 0 and np.isfinite(velocity) and np.isfinite(depth) else 0
                                
                                # 计算剪切应力
                                if self.channel_slope is not None:
                                    shear_stress[i, j] = self.water_density * self.g * hydraulic_radius[i, j] * self.channel_slope if np.isfinite(hydraulic_radius[i, j]) else 0
            
            # 计算流量统计
            valid_discharge = self.discharge[np.isfinite(self.discharge)]
            max_discharge = np.max(valid_discharge) if len(valid_discharge) > 0 else 0
            min_discharge = np.min(valid_discharge) if len(valid_discharge) > 0 else 0
            avg_discharge = np.mean(valid_discharge) if len(valid_discharge) > 0 else 0
            discharge_variation = np.std(valid_discharge) if len(valid_discharge) > 0 else 0
            
            # 计算水深统计
            valid_depth = self.water_depth[np.isfinite(self.water_depth)]
            max_depth = np.max(valid_depth) if len(valid_depth) > 0 else 0
            min_depth = np.min(valid_depth) if len(valid_depth) > 0 else 0
            avg_depth = np.mean(valid_depth) if len(valid_depth) > 0 else 0
            
            # 计算流速统计
            valid_velocity = self.velocity[np.isfinite(self.velocity)]
            max_velocity = np.max(valid_velocity) if len(valid_velocity) > 0 else 0
            min_velocity = np.min(valid_velocity) if len(valid_velocity) > 0 else 0
            avg_velocity = np.mean(valid_velocity) if len(valid_velocity) > 0 else 0
            
            # 计算弗劳德数统计
            valid_froude = froude_number[np.isfinite(froude_number)]
            max_froude = np.max(valid_froude) if len(valid_froude) > 0 else 0
            min_froude = np.min(valid_froude) if len(valid_froude) > 0 else 0
            avg_froude = np.mean(valid_froude) if len(valid_froude) > 0 else 0
            
            # 准备结果
            results = {
                'water_depth': self.water_depth,
                'velocity': self.velocity,
                'discharge': self.discharge,
                'water_surface_elevation': self.water_surface_elevation,
                'hydraulic_radius': hydraulic_radius,
                'wetted_perimeter': wetted_perimeter,
                'flow_area': flow_area,
                'froude_number': froude_number,
                'reynolds_number': reynolds_number,
                'shear_stress': shear_stress,
                'time_points': self.time_points,
                'space_points': self.space_points,
                'parameters': params,
                'channel_shape': self.channel_shape,
                'statistics': {
                    'max_discharge': float(max_discharge),
                    'min_discharge': float(min_discharge),
                    'avg_discharge': float(avg_discharge),
                    'discharge_variation': float(discharge_variation),
                    'max_depth': float(max_depth),
                    'min_depth': float(min_depth),
                    'avg_depth': float(avg_depth),
                    'max_velocity': float(max_velocity),
                    'min_velocity': float(min_velocity),
                    'avg_velocity': float(avg_velocity),
                    'max_froude': float(max_froude),
                    'min_froude': float(min_froude),
                    'avg_froude': float(avg_froude),
                    'flow_regime': '超临界流' if max_froude > 1 else '亚临界流',
                    'total_simulation_time': float(self.nt * self.dt),
                    'total_channel_length': float(self.nx * self.dx)
                },
                'diagnostics': getattr(self, '_diagnostics', {}),
                'success': True,
                'message': 'Saint-Venant模型运行成功'
            }
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Saint-Venant模型运行失败: {str(e)}',
                'error': str(e),
                'diagnostics': getattr(self, '_diagnostics', {})
            }
    
    def plot_results(self, results: Dict, save_path: Optional[str] = None):
        """
        绘制模型结果
        
        :param results: 模型结果字典
        :param save_path: 保存路径（可选）
        """
        if not results.get('success', False):
            print("无法绘制结果：模型运行失败")
            return
            
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'Saint-Venant水动力模型结果 - {self.channel_shape}渠道', fontsize=16)
        
        # 水深等值线图
        im1 = axes[0, 0].contourf(results['space_points'], results['time_points'], 
                                  results['water_depth'], levels=20)
        axes[0, 0].set_xlabel('距离 (m)')
        axes[0, 0].set_ylabel('时间 (s)')
        axes[0, 0].set_title('水深分布 (m)')
        plt.colorbar(im1, ax=axes[0, 0])
        
        # 流速等值线图
        im2 = axes[0, 1].contourf(results['space_points'], results['time_points'], 
                                  results['velocity'], levels=20)
        axes[0, 1].set_xlabel('距离 (m)')
        axes[0, 1].set_ylabel('时间 (s)')
        axes[0, 1].set_title('流速分布 (m/s)')
        plt.colorbar(im2, ax=axes[0, 1])
        
        # 水面高程等值线图
        im3 = axes[0, 2].contourf(results['space_points'], results['time_points'], 
                                  results['water_surface_elevation'], levels=20)
        axes[0, 2].set_xlabel('距离 (m)')
        axes[0, 2].set_ylabel('时间 (s)')
        axes[0, 2].set_title('水面高程 (m)')
        plt.colorbar(im3, ax=axes[0, 2])
        
        # 流量时间序列（上游和下游）
        axes[1, 0].plot(results['time_points'], results['discharge'][:, 0], 
                        label='上游流量', linewidth=2)
        axes[1, 0].plot(results['time_points'], results['discharge'][:, -1], 
                        label='下游流量', linewidth=2)
        axes[1, 0].set_xlabel('时间 (s)')
        axes[1, 0].set_ylabel('流量 (m³/s)')
        axes[1, 0].set_title('流量时间序列')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # 水深时间序列（上游和下游）
        axes[1, 1].plot(results['time_points'], results['water_depth'][:, 0], 
                        label='上游水深', linewidth=2)
        axes[1, 1].plot(results['time_points'], results['water_depth'][:, -1], 
                        label='下游水深', linewidth=2)
        axes[1, 1].set_xlabel('时间 (s)')
        axes[1, 1].set_ylabel('水深 (m)')
        axes[1, 1].set_title('水深时间序列')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
        
        # 渠道横断面图（最终时刻）
        final_depth = results['water_depth'][-1, :]
        axes[1, 2].plot(results['space_points'], final_depth, 'b-', linewidth=2, label='水深')
        axes[1, 2].fill_between(results['space_points'], 0, final_depth, alpha=0.3, color='blue')
        axes[1, 2].set_xlabel('距离 (m)')
        axes[1, 2].set_ylabel('水深 (m)')
        axes[1, 2].set_title('最终时刻水深分布')
        axes[1, 2].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"结果图已保存到: {save_path}")
        
        plt.show()
        
    def export_results(self, results: Dict, file_path: str):
        """
        导出结果到Excel文件
        
        :param results: 模型结果字典
        :param file_path: 导出文件路径
        """
        if not results.get('success', False):
            print("无法导出结果：模型运行失败")
            return
            
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 导出参数
                params_df = pd.DataFrame([results['parameters']])
                params_df.to_excel(writer, sheet_name='模型参数', index=False)
                
                # 导出水深数据
                depth_df = pd.DataFrame(results['water_depth'], 
                                      columns=[f'位置_{i*self.dx}m' for i in range(self.nx)],
                                      index=[f'时间_{i*self.dt}s' for i in range(self.nt)])
                depth_df.to_excel(writer, sheet_name='水深分布')
                
                # 导出流速数据
                velocity_df = pd.DataFrame(results['velocity'],
                                         columns=[f'位置_{i*self.dx}m' for i in range(self.nx)],
                                         index=[f'时间_{i*self.dt}s' for i in range(self.nt)])
                velocity_df.to_excel(writer, sheet_name='流速分布')
                
                # 导出流量数据
                discharge_df = pd.DataFrame(results['discharge'],
                                          columns=[f'位置_{i*self.dx}m' for i in range(self.nx)],
                                          index=[f'时间_{i*self.dt}s' for i in range(self.nt)])
                discharge_df.to_excel(writer, sheet_name='流量分布')
                
                # 导出水面高程数据
                elevation_df = pd.DataFrame(results['water_surface_elevation'],
                                          columns=[f'位置_{i*self.dx}m' for i in range(self.nx)],
                                          index=[f'时间_{i*self.dt}s' for i in range(self.nt)])
                elevation_df.to_excel(writer, sheet_name='水面高程')
                
            print(f"结果已成功导出到: {file_path}")
            
        except Exception as e:
            print(f"导出结果失败: {str(e)}")
            
    def get_parameter_summary(self):
        """获取参数摘要信息"""
        summary = {
            "模型类型": "Saint-Venant",
            "渠道形状": self.channel_shape,
            "空间步长": f"{self.dx} m",
            "时间步长": f"{self.dt} s",
            "空间网格数": self.nx,
            "时间网格数": self.nt,
            "Manning粗糙系数": self.manning_n,
            "渠道宽度": f"{self.channel_width} m",
            "渠道坡度": self.channel_slope,
            "侧向入流": f"{self.lateral_inflow} m³/s/m",
            "侧向出流": f"{self.lateral_outflow} m³/s/m",
            "风速": f"{self.wind_speed} m/s",
            "风向": f"{self.wind_direction}°",
            "水温": f"{self.water_temperature}°C"
        }
        return summary
