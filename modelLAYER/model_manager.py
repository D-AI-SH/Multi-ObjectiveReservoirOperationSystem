from .scs_cn_model import SCS_CN_Model
from .saint_venant_model import SaintVenantModel

class ModelManager:
    """
    模型管理器，负责调度模型的管理和运行。
    """
    def __init__(self):
        self.model = None
        self.results = None

    def select_model(self, model_name):
        """
        选择要使用的模型。
        """
        if model_name == "SCS-CN":
            self.model = SCS_CN_Model()
            print("已选择 SCS-CN 模型。")
        elif model_name == "Saint-Venant":
            self.model = SaintVenantModel()
            print("已选择 Saint-Venant 水动力模型。")
        else:
            print(f"警告：不支持的模型 '{model_name}'。")
            self.model = None

    def run_model(self, data, params):
        """
        使用给定的数据和参数运行模型。
        """
        if self.model is None:
            print("错误：未选择任何模型。")
            return None
        
        print("正在运行模型...")
        self.results = self.model.run(data, params)
        print("模型运行完成。")
        
        # 检查结果是否成功
        if isinstance(self.results, dict):
            if not self.results.get('success', False):
                print(f"模型运行失败: {self.results.get('message', '未知错误')}")
                return None
            
            # 将字典结果转换为DataFrame格式
            return self._convert_results_to_dataframe(self.results)
        
        return self.results
    
    def _convert_results_to_dataframe(self, results_dict):
        """
        将Saint-Venant模型的结果字典转换为DataFrame格式
        """
        import pandas as pd
        import numpy as np
        
        try:
            # 创建时间与空间序列数据（兼容 numpy 数组/列表）
            time_points = results_dict.get('time_points', [])
            space_points = results_dict.get('space_points', [])

            # 避免对 numpy.ndarray 直接使用 `if not arr` 导致的歧义错误
            if time_points is None or space_points is None:
                print("警告：缺少时间或空间点数据")
                return None
            if len(time_points) == 0 or len(space_points) == 0:
                print("警告：时间或空间点数据长度为0")
                return None
            
            # 创建DataFrame，包含时间、空间位置和主要结果
            data = []
            
            # 对于每个时间点和空间点，创建一行数据
            for i, t in enumerate(time_points):
                for j, x in enumerate(space_points):
                    row = {
                        'time': t,
                        'space': x,
                        'water_depth': results_dict['water_depth'][i, j] if 'water_depth' in results_dict else np.nan,
                        'velocity': results_dict['velocity'][i, j] if 'velocity' in results_dict else np.nan,
                        'discharge': results_dict['discharge'][i, j] if 'discharge' in results_dict else np.nan,
                        'water_surface_elevation': results_dict['water_surface_elevation'][i, j] if 'water_surface_elevation' in results_dict else np.nan,
                        'froude_number': results_dict['froude_number'][i, j] if 'froude_number' in results_dict else np.nan,
                        'hydraulic_radius': results_dict['hydraulic_radius'][i, j] if 'hydraulic_radius' in results_dict else np.nan,
                        'flow_area': results_dict['flow_area'][i, j] if 'flow_area' in results_dict else np.nan,
                        'reservoir_id': 1  # 默认水库ID
                    }
                    data.append(row)
            
            df = pd.DataFrame(data)
            
            # 添加模型参数作为属性
            df.attrs['model_parameters'] = results_dict.get('parameters', {})
            df.attrs['channel_shape'] = results_dict.get('channel_shape', '')
            df.attrs['statistics'] = results_dict.get('statistics', {})
            df.attrs['success'] = True
            df.attrs['message'] = '模型运行成功'
            
            return df
            
        except Exception as e:
            print(f"转换结果到DataFrame时出错: {str(e)}")
            return None
