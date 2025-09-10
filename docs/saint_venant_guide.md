# Saint-Venant水动力模型使用指南

## 概述

Saint-Venant水动力模型是一个基于一维明渠非恒定流基本方程的数值求解器。该模型可以模拟河流、渠道等水体的水流运动，包括水深、流速和流量的时空变化。

## 理论基础

### Saint-Venant方程组

Saint-Venant方程组由两个基本方程组成：

1. **连续性方程**：
   ```
   ∂h/∂t + ∂(h*v)/∂x = 0
   ```
   其中：
   - h：水深 (m)
   - v：流速 (m/s)
   - t：时间 (s)
   - x：距离 (m)

2. **动量方程**：
   ```
   ∂v/∂t + v*∂v/∂x + g*∂h/∂x = g*(S₀ - Sf)
   ```
   其中：
   - g：重力加速度 (9.81 m/s²)
   - S₀：渠道底坡
   - Sf：摩擦坡度

### 摩擦坡度计算

使用Manning公式计算摩擦坡度：
```
Sf = (n² * v²) / (R^(4/3))
```
其中：
- n：Manning粗糙系数
- R：水力半径 (m)

## 模型参数

### 基本参数

| 参数名 | 单位 | 默认值 | 说明 |
|--------|------|--------|------|
| `dx` | m | 100.0 | 空间步长 |
| `dt` | s | 1.0 | 时间步长 |
| `nx` | - | 100 | 空间网格数 |
| `nt` | - | 1000 | 时间网格数 |
| `manning_n` | - | 0.015 | Manning粗糙系数 |
| `channel_width` | m | 10.0 | 渠道宽度 |
| `channel_slope` | - | 0.001 | 渠道坡度 |

### 参数选择建议

1. **空间步长 (dx)**：
   - 对于长距离模拟：100-500 m
   - 对于局部精细模拟：10-50 m

2. **时间步长 (dt)**：
   - 需要满足CFL条件：dt ≤ dx / (v + √(gh))
   - 通常选择：1-10 s

3. **Manning粗糙系数 (n)**：
   - 混凝土渠道：0.012-0.015
   - 土质渠道：0.020-0.030
   - 天然河道：0.030-0.050

## 输入数据格式

### 必需数据

模型需要以下输入数据：

```python
input_data = pd.DataFrame({
    'upstream_discharge': upstream_discharge,  # 上游流量时间序列 (m³/s)
    'downstream_depth': downstream_depth,      # 下游水深时间序列 (m)
    'initial_depth': initial_depth,            # 初始水深分布 (m)
    'initial_velocity': initial_velocity       # 初始流速分布 (m/s)
})
```

### 数据要求

1. **上游流量**：长度必须等于时间步数 (nt)
2. **下游水深**：长度必须等于时间步数 (nt)
3. **初始水深**：长度必须等于空间网格数 (nx)
4. **初始流速**：长度必须等于空间网格数 (nx)

## 使用方法

### 基本使用

```python
from saint_venant_model import SaintVenantModel

# 创建模型实例
model = SaintVenantModel()

# 设置参数
params = {
    'dx': 100.0,
    'dt': 1.0,
    'nx': 100,
    'nt': 1000,
    'manning_n': 0.015,
    'channel_width': 15.0,
    'channel_slope': 0.001
}

# 运行模型
results = model.run(input_data, params)

# 检查结果
if results['success']:
    print("模型运行成功!")
    # 访问结果数据
    water_depth = results['water_depth']
    velocity = results['velocity']
    discharge = results['discharge']
else:
    print(f"模型运行失败: {results['message']}")
```

### 结果可视化

```python
# 绘制结果
model.plot_results(results, save_path="results.png")

# 导出结果到Excel
model.export_results(results, "results.xlsx")
```

## 输出结果

### 结果字典结构

```python
results = {
    'water_depth': water_depth,      # 水深分布 (nt × nx)
    'velocity': velocity,            # 流速分布 (nt × nx)
    'discharge': discharge,          # 流量分布 (nt × nx)
    'time_points': time_points,      # 时间点数组
    'space_points': space_points,    # 空间点数组
    'parameters': params,            # 模型参数
    'success': True,                 # 运行状态
    'message': '运行成功信息'
}
```

### 结果解释

1. **水深分布**：二维数组，行表示时间，列表示空间位置
2. **流速分布**：二维数组，行表示时间，列表示空间位置
3. **流量分布**：二维数组，行表示时间，列表示空间位置

## 应用场景

### 适用情况

1. **洪水演进模拟**：模拟洪水在河道中的传播过程
2. **渠道设计**：评估渠道的过流能力和稳定性
3. **水质模拟**：结合水质模型进行污染物输运模拟
4. **水库调度**：分析水库放水对下游的影响

### 限制条件

1. **一维假设**：假设水流主要沿渠道方向运动
2. **明渠流动**：适用于自由水面流动
3. **数值稳定性**：需要满足CFL条件确保数值稳定

## 示例应用

### 洪水演进模拟

```python
# 创建洪水过程线
def create_flood_hydrograph(nt, base_flow, peak_flow, peak_time):
    """创建三角形洪水过程线"""
    time_points = np.arange(nt)
    discharge = np.zeros(nt)
    
    for i, t in enumerate(time_points):
        if t <= peak_time:
            discharge[i] = base_flow + (peak_flow - base_flow) * (t / peak_time)
        else:
            remaining_time = nt - peak_time
            discharge[i] = peak_flow - (peak_flow - base_flow) * ((t - peak_time) / remaining_time)
    
    return discharge

# 设置洪水参数
base_flow = 50.0      # 基流 (m³/s)
peak_flow = 200.0     # 峰值流量 (m³/s)
peak_time = 1800      # 峰值时间 (s)

# 创建输入数据
upstream_discharge = create_flood_hydrograph(nt, base_flow, peak_flow, peak_time)
```

### 参数敏感性分析

```python
# 测试不同Manning系数的影响
manning_values = [0.010, 0.015, 0.020, 0.025]
results_comparison = {}

for manning_n in manning_values:
    test_params = params.copy()
    test_params['manning_n'] = manning_n
    
    results = model.run(input_data, test_params)
    if results['success']:
        max_depth = np.max(results['water_depth'])
        results_comparison[manning_n] = max_depth
```

## 故障排除

### 常见问题

1. **数值不稳定**：
   - 减小时间步长
   - 检查CFL条件
   - 调整空间步长

2. **边界条件问题**：
   - 确保边界条件合理
   - 检查数据长度匹配

3. **内存不足**：
   - 减少网格数量
   - 增加步长

### 调试建议

1. 使用小规模测试案例验证模型
2. 检查输入数据的合理性
3. 监控数值稳定性指标

## 扩展功能

### 未来改进方向

1. **二维扩展**：支持平面二维水流模拟
2. **复杂地形**：支持不规则渠道断面
3. **耦合模型**：与水质、泥沙模型耦合
4. **并行计算**：支持大规模并行计算

## 参考文献

1. Chow, V.T. (1959). Open-Channel Hydraulics. McGraw-Hill.
2. Cunge, J.A., Holly, F.M., & Verwey, A. (1980). Practical Aspects of Computational River Hydraulics. Pitman.
3. Sturm, T.W. (2001). Open Channel Hydraulics. McGraw-Hill.

## 技术支持

如有问题或建议，请联系开发团队或查看项目文档。
