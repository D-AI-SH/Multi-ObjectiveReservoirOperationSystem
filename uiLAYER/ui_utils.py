from PyQt6.QtCore import QAbstractTableModel, Qt

# 定义模型需要的数据
MODEL_DATA_REQUIREMENTS = {
    "SCS-CN": [
        "precipitation",  # 必需：降雨量
        "temperature",    # 可选：温度
        "evaporation",    # 可选：蒸发量
        # "antecedent_rainfall"  # 已移除：现在由系统自动计算
    ],
    "Saint-Venant": [
        "upstream_discharge",   # 必需：上游流量（边界条件）
        "downstream_depth",     # 必需：下游水深（边界条件）
        "wind_speed",           # 可选：风速（时间序列或常数）
        "wind_direction",       # 可选：风向（时间序列或常数）
        "water_temperature"     # 可选：水温（时间序列或常数）
    ],
    "其他模型...": ["evaporation", "temperature_avg"]
}

# UI显示名称翻译字典
TRANSLATIONS = {
    # 基本气象数据
    "precipitation": "降雨量",
    "temperature": "温度",
    "evaporation": "蒸发量",
    # "antecedent_rainfall": "前期降雨量",  # 已移除：现在由系统自动计算
    
    # 水文数据
    "upstream_discharge": "上游流量",
    "downstream_depth": "下游水深",
    "initial_depth": "初始水深",
    "initial_velocity": "初始流速",
    "lateral_inflow": "侧向入流",
    "lateral_outflow": "侧向出流",
    
    # 气象数据
    "wind_speed": "风速",
    "wind_direction": "风向",
    "water_temperature": "水温",
    
    # 原有数据
    "temperature_avg": "平均温度",
    "temperature_min": "最低温度",
    "temperature_max": "最高温度",
    "wind_speed_avg": "平均风速",
    "wind_speed_max": "最大风速",
    "pressure_avg": "平均气压",
    "pressure_min": "最低气压",
    "pressure_max": "最高气压",
    "humidity_avg": "平均相对湿度",
    "humidity_min": "最低相对湿度",
    "vapor_pressure_avg": "平均水汽压",
    "sunshine_hours": "日照时数"
}

class PandasModel(QAbstractTableModel):
    """一个将Pandas DataFrame提供给QTableView的模型。"""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._data.columns[col]
        return None
