#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例参数配置文件
包含SCS-CN和圣维南模型的示例参数
"""

# SCS-CN模型示例参数
SCS_CN_EXAMPLE_PARAMS = {
    "basic": {
        "CN": 70.0,  # 径流曲线数
        "Ia_coefficient": 0.2,  # 初始抽象量系数
        "land_use": "行作物",  # 土地利用类型
        "soil_type": "C",  # 土壤类型
        "vegetation_cover": 0.5,  # 植被覆盖度
        "slope": 5.0  # 坡度 (%)
    },
    "climate": {
        "antecedent_days": 5.0,  # 前期降雨天数
        "auto_calculate_antecedent": True,  # 自动计算前期降雨量
        "antecedent_rainfall": 20.0,  # 前期5天降雨量 (mm) - 手动设置时使用
        "temperature": 20.0,  # 温度 (℃)
        "evaporation": 2.0  # 蒸发量 (mm)
    }
}

# 圣维南模型示例参数
SAINT_VENANT_EXAMPLE_PARAMS = {
    "basic": {
        "dx": 100.0,  # 空间步长 (m)
        "dt": 10.0,   # 时间步长 (s)
        "nx": 50,     # 空间网格数
        "nt": 80,     # 时间步数
        "channel_width": 10.0,  # 渠道宽度 (m)
        "channel_slope": 0.001,  # 渠道坡度
        "manning_n": 0.015,  # Manning粗糙系数
        "channel_shape": "矩形"  # 渠道形状
    },
    "default_values": {
        "default_upstream_discharge": 4.5,  # 默认上游流量4.5 m³/s
        "default_downstream_depth": 1.2,  # 默认下游水深1.2 m
        "default_initial_depth": 1.0,  # 默认初始水深1.0 m
        "default_initial_velocity": 0.5  # 默认初始流速0.5 m/s
    },
    "physical_constants": {
        "gravity": 9.81,  # 重力加速度 (m/s²)
        "water_density": 1000.0,  # 水的密度 (kg/m³)
        "air_density": 1.225,  # 空气密度 (kg/m³)
        "kinematic_viscosity": 1e-6,  # 水的运动粘性系数 (m²/s)
        "reference_temperature": 20.0,  # 参考温度 (℃)
        "thermal_expansion_coefficient": 0.02,  # 温度膨胀系数
        "wind_drag_coefficient": 0.0013  # 风阻力系数
    },
    "boundary_conditions": {
        "upstream_type": "流量",  # 上游边界条件类型
        "downstream_type": "水深",  # 下游边界条件类型
        "wind_speed": 5.0,  # 风速 (m/s)
        "wind_direction": 0.0,  # 风向 (度)
        "water_temperature": 20.0  # 水温 (℃)
    },
    "numerical_parameters": {
        "cfl_limit": 0.8,  # CFL数限制
        "max_iterations": 1000,  # 最大迭代次数
        "convergence_tolerance": 1e-6,  # 收敛容差
        "stability_factor": 0.9,  # 稳定性因子
        "max_depth_limit": 100.0,  # 最大水深限制 (m)
        "min_depth_limit": 0.001,  # 最小水深限制 (m)
        "max_velocity_limit": 50.0,  # 最大流速限制 (m/s)
        "min_velocity_limit": -50.0,  # 最小流速限制 (m/s)
        "max_discharge_limit": 50000.0,  # 最大流量限制 (m³/s)
        "min_discharge_limit": -10000.0  # 最小流量限制 (m³/s)
    }
}

# 示例数据文件路径
EXAMPLE_DATA_FILES = {
    "SCS-CN": "example_data/scs_cn_example_data.csv",
    "Saint-Venant": "example_data/saint_venant_example_data.csv"
}

# 示例数据描述
EXAMPLE_DATA_DESCRIPTIONS = {
    "SCS-CN": {
        "name": "SCS-CN模型示例数据",
        "description": "包含30天的降雨、流量、水位、温度和蒸发量数据",
        "features": [
            "降雨数据：包含0值（无降雨日）和不同强度的降雨",
            "流量数据：对应降雨的径流响应",
            "水位数据：水库水位变化",
            "温度数据：日平均温度变化",
            "蒸发量：日蒸发量数据",
            "前期降雨量：系统自动计算（基于降雨数据）"
        ],
        "data_columns": ["date", "rainfall", "flow", "water_level", "temperature", "evaporation"],
        "date_range": "2024-01-01 到 2024-01-30",
        "records": 30
    },
         "Saint-Venant": {
         "name": "圣维南模型示例数据",
         "description": "包含13.3小时的边界条件和环境参数数据，时间间隔10分钟，设计为数值稳定",
         "features": [
             "上游流量：渠道上游边界流量变化（4.25-5.05 m³/s，变化幅度仅18.8%）",
             "下游水深：渠道下游边界水深变化（1.0-1.8m，变化幅度仅80%）",
             "风速：时间序列风速数据（1.5 m/s，恒定风速）",
             "风向：时间序列风向数据（45度，恒定风向）",
             "水温：时间序列水温数据（18.5-22.5℃，缓慢变化）"
         ],
         "data_columns": ["date", "upstream_discharge", "downstream_depth", "wind_speed", "wind_direction", "water_temperature"],
         "date_range": "2024-01-01 00:00:00 到 2024-01-01 13:20:00",
         "records": 80
     }
}

# 参数描述
PARAMETER_DESCRIPTIONS = {
    "SCS-CN": {
        "basic": {
            "CN": "径流曲线数，反映土壤渗透性和土地利用特征，范围30-100",
            "Ia_coefficient": "初始抽象量系数，通常取0.2"
        },
        "land_use": {
            "land_use": "土地利用类型，影响径流产生",
            "soil_type": "土壤类型，A/B/C/D表示渗透性递减",
            "vegetation_cover": "植被覆盖度，0-1之间",
            "slope": "地形坡度，影响径流速度"
        },
        "climate": {
            "antecedent_days": "前期降雨天数，系统自动计算前期降雨量的时间窗口",
            "auto_calculate_antecedent": "是否自动计算前期降雨量，推荐启用",
            "antecedent_rainfall": "手动设置的前期降雨量（仅在自动计算关闭时使用）",
            "temperature": "温度，影响蒸发",
            "evaporation": "蒸发量，影响水量平衡"
        }
    },
    "Saint-Venant": {
        "basic": {
            "dx": "空间步长，数值计算的空间分辨率",
            "dt": "时间步长，数值计算的时间分辨率",
            "nx": "空间网格数，计算域的空间划分",
            "nt": "时间网格数，计算时间段的划分",
            "manning_n": "Manning粗糙系数，反映渠道粗糙度",
            "channel_width": "渠道宽度",
            "channel_slope": "渠道坡度"
        },
        "channel_shape": {
            "channel_shape": "渠道形状类型",
            "side_slope": "边坡系数，梯形渠道的边坡",
            "parabola_coefficient": "抛物线系数，抛物线形渠道参数",
            "radius": "圆形渠道半径"
        },
                 "initial_conditions": {
             "initial_depth": "初始水深，渠道初始水深分布",
             "initial_velocity": "初始流速，渠道初始流速分布"
         },
         "lateral_flow": {
             "lateral_inflow": "侧向入流，单位长度入流量",
             "lateral_outflow": "侧向出流，单位长度出流量"
         },
        "optional_features": {
            "enable_lateral_flow": "启用侧向流计算，影响水量平衡",
            "enable_wind_effects": "启用风应力效应，影响水面摩擦",
            "enable_temperature_effects": "启用温度效应，影响流体性质"
        }
    }
}
