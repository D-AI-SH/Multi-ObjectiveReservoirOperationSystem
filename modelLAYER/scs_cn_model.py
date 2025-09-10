import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union

class SCS_CN_Model:
    """
    SCS-CN（Soil Conservation Service Curve Number）模型实现。
    用于计算降雨-径流关系，考虑土地利用、土壤类型和前期土壤湿度条件。
    """
    
    def __init__(self):
        """初始化SCS-CN模型"""
        self.parameters = {}
        self.results = {}
        
        # 土地利用对应的CN值（AMC II条件下）
        self.LAND_USE_CN = {
            "行作物": {"直行": 72, "等高": 67, "等高+梯田": 64},
            "小粒谷物": {"直行": 65, "等高": 63, "等高+梯田": 61},
            "牧草": {"差": 79, "一般": 69, "好": 58},
            "林地": {"差": 77, "一般": 70, "好": 55},
            "湿地": {"差": 89, "一般": 84, "好": 80},
            "森林": {"差": 77, "一般": 70, "好": 55},
            "草地": {"差": 79, "一般": 69, "好": 58},
            "灌木": {"差": 77, "一般": 70, "好": 55},
            "裸地": {"差": 89, "一般": 84, "好": 80},
            "城市建成区": {"不透水": 98, "半透水": 89, "透水": 61}
        }
        
        # 土壤类型特征
        self.SOIL_TYPE_CHARACTERISTICS = {
            "A": {"infiltration_rate": "高", "runoff_potential": "低", "description": "砂质土壤，渗透性好"},
            "B": {"infiltration_rate": "中高", "runoff_potential": "中低", "description": "粉质砂土，渗透性较好"},
            "C": {"infiltration_rate": "中", "runoff_potential": "中", "description": "粉质粘土，渗透性中等"},
            "D": {"infiltration_rate": "低", "runoff_potential": "高", "description": "粘土，渗透性差"}
        }
        
        # 默认参数
        self.default_parameters = {
            "CN": 70,
            "Ia_coefficient": 0.2,
            "land_use": "行作物",
            "soil_type": "C",
            "vegetation_cover": 0.5,
            "slope": 5.0,
            "antecedent_days": 5,  # 前期降雨天数，默认5天
            "auto_calculate_antecedent": True  # 是否自动计算前期降雨量
        }
        
        # 初始化默认参数
        for key, value in self.default_parameters.items():
            self.parameters[key] = value

    def set_parameters(self, params: Dict[str, Any]):
        """
        设置模型参数。
        
        :param params: 参数字典，包含以下键：
        - CN: 径流曲线数
        - Ia_coefficient: 初始抽象量系数
        - land_use: 土地利用类型
        - soil_type: 土壤类型 (A, B, C, D)
        - vegetation_cover: 植被覆盖度 (0-1)
        - slope: 坡度 (%)
        - antecedent_rainfall: 前期降雨量 (mm)，如果提供则使用固定值
        - antecedent_days: 前期降雨天数，用于自动计算
        - auto_calculate_antecedent: 是否自动计算前期降雨量
        """
        # 更新参数
        for key, value in params.items():
            if key in self.default_parameters:
                self.parameters[key] = value
        
        # 如果没有直接提供CN，则根据土地利用和土壤类型计算
        if 'CN' not in params:
            self.parameters['CN'] = self._calculate_CN_from_land_use()
            
        # 处理前期降雨量参数
        if 'antecedent_rainfall' in params and not params.get('auto_calculate_antecedent', True):
            # 用户提供了固定值，直接使用
            self.parameters['amc_condition'] = self._determine_AMC_condition(
                params['antecedent_rainfall']
            )
        # 如果没有提供固定值或启用了自动计算，将在运行时计算
            
        # 调整CN值根据AMC条件（如果已确定）
        if 'amc_condition' in self.parameters:
            self.parameters['CN'] = self._adjust_CN_for_AMC()

    def _calculate_antecedent_rainfall(self, rainfall_data: np.ndarray, antecedent_days: int = 5) -> np.ndarray:
        """
        自动计算前期降雨量。
        
        :param rainfall_data: 降雨量数组
        :param antecedent_days: 前期天数
        :return: 每个时间点的前期降雨量数组
        """
        # 确保antecedent_days是整数类型
        antecedent_days = int(antecedent_days)
        
        if antecedent_days <= 0:
            return np.zeros_like(rainfall_data)
            
        antecedent_rainfall = np.zeros_like(rainfall_data)
        
        for i in range(len(rainfall_data)):
            if i < antecedent_days:
                # 对于前几个点，使用可用的历史数据
                start_idx = 0
            else:
                # 使用滑动窗口，确保索引不为负数
                start_idx = max(0, i - antecedent_days)
                
            # 计算滑动窗口内的累积降雨量
            antecedent_rainfall[i] = np.sum(rainfall_data[start_idx:i])
            
        return antecedent_rainfall

    def _determine_AMC_condition(self, antecedent_rainfall: float) -> str:
        """
        根据前期5天降雨量确定AMC条件
        
        :param antecedent_rainfall: 前期降雨量 (mm)
        :return: AMC条件 ('I', 'II', 或 'III')
        """
        if antecedent_rainfall < 13:
            return 'I'  # 干旱条件
        elif antecedent_rainfall < 28:
            return 'II'  # 正常条件
        else:
            return 'III'  # 湿润条件

    def _adjust_CN_for_AMC(self) -> float:
        """
        根据AMC条件调整CN值
        
        :return: 调整后的CN值
        """
        cn_ii = self.parameters['CN']  # AMC II条件下的CN值
        amc_condition = self.parameters['amc_condition']
        
        if amc_condition == 'I':
            # AMC I: CN_I = CN_II / (2.334 - 0.01334 * CN_II)
            return cn_ii / (2.334 - 0.01334 * cn_ii)
        elif amc_condition == 'III':
            # AMC III: CN_III = CN_II / (0.4036 + 0.0059 * CN_II)
            return cn_ii / (0.4036 + 0.0059 * cn_ii)
        else:
            return cn_ii  # AMC II
            
    def _calculate_CN_from_land_use(self) -> float:
        """
        根据土地利用类型和土壤类型计算CN值
        
        :return: 计算得到的CN值
        """
        land_use = self.parameters.get('land_use', '行作物')
        soil_type = self.parameters.get('soil_type', 'C')
        
        # 获取土地利用对应的CN值
        if land_use in self.LAND_USE_CN:
            # 简化处理，取第一个子类型
            cn_value = list(self.LAND_USE_CN[land_use].values())[0]
        else:
            cn_value = 70  # 默认值
            
        # 根据土壤类型调整
        soil_adjustments = {'A': -10, 'B': -5, 'C': 0, 'D': 5}
        adjustment = soil_adjustments.get(soil_type, 0)
        
        return max(30, min(100, cn_value + adjustment))

    def calculate_runoff(self, P: np.ndarray, additional_params: Optional[Dict[str, np.ndarray]] = None) -> np.ndarray:
        """
        根据给定的降雨量(P)和模型参数计算径流(Q)。
        
        :param P: 降雨量数组 (mm)
        :param additional_params: 额外的时变参数（如温度、蒸发等）
        :return: 径流量数组 (mm)
        """
        P = np.array(P, dtype=float)
        CN = self.parameters['CN']
        Ia_coefficient = self.parameters.get('Ia_coefficient', 0.2)
        
        # 计算潜在最大滞留量
        S = (1000 / CN) - 10
        
        # 计算初始抽象量
        Ia = Ia_coefficient * S
        
        # 如果有温度数据，考虑温度对蒸发的影响
        if additional_params and 'temperature' in additional_params:
            temp = additional_params['temperature']
            # 简化的温度修正
            temp_factor = 1 + 0.02 * (temp - 20)  # 20℃为基准温度
            Ia = Ia * temp_factor
            
        # 如果有蒸发数据，考虑蒸发对径流的影响
        if additional_params and 'evaporation' in additional_params:
            evap = additional_params['evaporation']
            # 蒸发减少有效降雨量
            P_effective = np.maximum(P - evap, 0)
        else:
            P_effective = P
            
        # 计算径流
        Q = np.where(P_effective > Ia, 
                    ((P_effective - Ia)**2) / (P_effective - Ia + S), 
                    0)
        
        return Q

    def run(self, input_df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """
        运行模型。

        :param input_df: 包含所有模型所需列的、已准备好的DataFrame。
                         对于SCS-CN，需要 'precipitation' 列。
                         可选列：'temperature', 'evaporation'
        :param params: 包含模型参数的字典
        :return: 包含输入和结果的DataFrame
        """
        # 设置参数
        self.set_parameters(params)
        
        # 检查必需的数据列
        if 'precipitation' not in input_df.columns:
            raise ValueError("输入DataFrame必须包含 'precipitation' 列。")
            
        # 准备额外参数
        additional_params = {}
        for col in ['temperature', 'evaporation']:
            if col in input_df.columns:
                additional_params[col] = input_df[col].values
                
        # 计算径流
        P = input_df['precipitation']
        
        # 自动计算前期降雨量
        if self.parameters.get('auto_calculate_antecedent', True):
            antecedent_rainfall = self._calculate_antecedent_rainfall(
                P.values, self.parameters.get('antecedent_days', 5)
            )
            # 根据自动计算的前期降雨量确定AMC条件
            self.parameters['amc_condition'] = self._determine_AMC_condition(
                antecedent_rainfall[-1]  # 使用最后一个时间点的前期降雨量
            )
            # 调整CN值根据AMC条件
            self.parameters['CN'] = self._adjust_CN_for_AMC()
        
        runoff = self.calculate_runoff(P, additional_params)
        
        # 计算详细的水文参数
        CN = self.parameters['CN']
        S = (1000 / CN) - 10  # 潜在最大滞留量
        Ia_coefficient = self.parameters.get('Ia_coefficient', 0.2)
        Ia = Ia_coefficient * S  # 初始抽象量
        
        # 计算其他水文指标
        infiltration = np.maximum(P - runoff, 0)  # 下渗量
        effective_rainfall = np.maximum(P - Ia, 0)  # 有效降雨量
        runoff_coefficient = np.where(P > 0, runoff / P, 0)  # 径流系数
        
        # 计算累积值
        cumulative_precipitation = np.cumsum(P)
        cumulative_runoff = np.cumsum(runoff)
        cumulative_infiltration = np.cumsum(infiltration)
        
        # 准备结果
        results_df = input_df.copy()
        results_df['runoff'] = runoff
        results_df['infiltration'] = infiltration
        results_df['effective_rainfall'] = effective_rainfall
        results_df['runoff_coefficient'] = runoff_coefficient
        results_df['cumulative_precipitation'] = cumulative_precipitation
        results_df['cumulative_runoff'] = cumulative_runoff
        results_df['cumulative_infiltration'] = cumulative_infiltration
        
        # 添加模型参数信息
        results_df['CN_used'] = CN
        results_df['S_potential'] = S
        results_df['Ia_initial'] = Ia
        
        # 如果自动计算了前期降雨量，添加到结果中
        if self.parameters.get('auto_calculate_antecedent', True):
            results_df['antecedent_rainfall'] = antecedent_rainfall
            results_df['AMC_condition'] = self.parameters['amc_condition']
        
        # 计算统计信息
        stats = {
            'total_precipitation': float(np.sum(P)),
            'total_runoff': float(np.sum(runoff)),
            'total_infiltration': float(np.sum(infiltration)),
            'average_runoff_coefficient': float(np.mean(runoff_coefficient[P > 0])),
            'max_runoff': float(np.max(runoff)),
            'max_runoff_coefficient': float(np.max(runoff_coefficient)),
            'runoff_events': int(np.sum(runoff > 0)),
            'total_periods': len(P)
        }
        
        # 添加模型参数信息
        results_df.attrs['model_parameters'] = self.parameters
        results_df.attrs['model_type'] = 'SCS-CN'
        results_df.attrs['statistics'] = stats
        results_df.attrs['calculation_summary'] = {
            'CN_value': CN,
            'potential_retention_S': S,
            'initial_abstraction_Ia': Ia,
            'Ia_coefficient': Ia_coefficient,
            'land_use_type': self.parameters.get('land_use', '未设置'),
            'soil_type': self.parameters.get('soil_type', '未设置'),
            'amc_condition': self.parameters.get('amc_condition', '未设置'),
            'vegetation_cover': self.parameters.get('vegetation_cover', '未设置'),
            'slope_percent': self.parameters.get('slope', '未设置'),
            'antecedent_days': self.parameters.get('antecedent_days', '未设置'),
            'auto_calculate_antecedent': self.parameters.get('auto_calculate_antecedent', '未设置')
        }
        
        return results_df

    def get_parameter_summary(self) -> Dict[str, Any]:
        """获取参数摘要信息"""
        summary = {
            "模型类型": "SCS-CN",
            "径流曲线数(CN)": self.parameters.get('CN', '未设置'),
            "土地利用类型": self.parameters.get('land_use', '未设置'),
            "土壤类型": self.parameters.get('soil_type', '未设置'),
            "前期土壤湿度条件": self.parameters.get('amc_condition', '未设置'),
            "初始抽象量系数": self.parameters.get('Ia_coefficient', 0.2),
            "前期降雨天数": self.parameters.get('antecedent_days', '未设置'),
            "自动计算前期降雨量": self.parameters.get('auto_calculate_antecedent', '未设置'),
            "植被覆盖度": self.parameters.get('vegetation_cover', '未设置'),
            "坡度": self.parameters.get('slope', '未设置')
        }
        
        # 如果手动设置了前期降雨量，也显示
        if 'antecedent_rainfall' in self.parameters:
            summary["前期5天降雨量"] = self.parameters['antecedent_rainfall']
            
        return summary
