#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saint-Venant水动力模型使用示例
演示如何使用Saint-Venant模型进行一维明渠非恒定流计算
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 添加模型层路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'modelLAYER'))

from saint_venant_model import SaintVenantModel

def create_sample_data():
    """
    创建示例输入数据
    """
    # 时间参数
    total_time = 3600  # 总时间 (s)
    dt = 1.0          # 时间步长 (s)
    nt = int(total_time / dt) + 1
    
    # 空间参数
    total_length = 10000  # 总长度 (m)
    dx = 100.0           # 空间步长 (m)
    nx = int(total_length / dx) + 1
    
    # 创建时间序列
    time_points = np.arange(nt) * dt
    
    # 上游流量：模拟洪水过程
    base_flow = 50.0  # 基流 (m³/s)
    peak_flow = 200.0  # 峰值流量 (m³/s)
    peak_time = 1800   # 峰值时间 (s)
    
    # 使用三角形洪水过程线
    upstream_discharge = np.zeros(nt)
    for i, t in enumerate(time_points):
        if t <= peak_time:
            # 上升段
            upstream_discharge[i] = base_flow + (peak_flow - base_flow) * (t / peak_time)
        else:
            # 下降段
            remaining_time = total_time - peak_time
            upstream_discharge[i] = peak_flow - (peak_flow - base_flow) * ((t - peak_time) / remaining_time)
    
    # 下游水深：保持相对稳定
    downstream_depth = np.ones(nt) * 2.5  # 下游水深 (m)
    
    # 初始条件：均匀分布
    initial_depth = np.ones(nx) * 2.0     # 初始水深 (m)
    initial_velocity = np.ones(nx) * 1.0  # 初始流速 (m/s)
    
    # 创建输入数据字典（避免DataFrame长度不匹配问题）
    input_data = {
        'upstream_discharge': upstream_discharge,
        'downstream_depth': downstream_depth,
        'initial_depth': initial_depth,
        'initial_velocity': initial_velocity
    }
    
    return input_data, nt, nx

def run_saint_venant_example():
    """
    运行Saint-Venant模型示例
    """
    print("=== Saint-Venant水动力模型示例 ===\n")
    
    # 创建示例数据
    print("1. 创建示例输入数据...")
    input_data, nt, nx = create_sample_data()
    print(f"   时间步数: {nt}")
    print(f"   空间网格数: {nx}")
    print(f"   总时间: {nt * 1.0:.0f} 秒")
    print(f"   总长度: {nx * 100.0:.0f} 米")
    
    # 设置模型参数
    print("\n2. 设置模型参数...")
    params = {
        'dx': 100.0,           # 空间步长 (m)
        'dt': 1.0,             # 时间步长 (s)
        'nx': nx,              # 空间网格数
        'nt': nt,              # 时间网格数
        'manning_n': 0.015,    # Manning粗糙系数
        'channel_width': 15.0, # 渠道宽度 (m)
        'channel_slope': 0.001 # 渠道坡度
    }
    
    print("   模型参数:")
    for key, value in params.items():
        print(f"     {key}: {value}")
    
    # 创建并运行模型
    print("\n3. 创建Saint-Venant模型...")
    model = SaintVenantModel()
    
    print("4. 运行模型...")
    results = model.run(input_data, params)
    
    if results['success']:
        print("   ✓ 模型运行成功!")
        print(f"   {results['message']}")
        
        # 显示结果摘要
        print("\n5. 结果摘要:")
        water_depth = results['water_depth']
        velocity = results['velocity']
        discharge = results['discharge']
        
        print(f"   水深范围: {np.min(water_depth):.3f} - {np.max(water_depth):.3f} m")
        print(f"   流速范围: {np.min(velocity):.3f} - {np.max(velocity):.3f} m/s")
        print(f"   流量范围: {np.min(discharge):.3f} - {np.max(discharge):.3f} m³/s")
        
        # 绘制结果
        print("\n6. 绘制结果...")
        model.plot_results(results, save_path="saint_venant_results.png")
        
        # 导出结果
        print("\n7. 导出结果...")
        model.export_results(results, "saint_venant_results.xlsx")
        
        print("\n=== 示例运行完成 ===")
        
    else:
        print(f"   ✗ 模型运行失败: {results['message']}")
        if 'error' in results:
            print(f"   错误详情: {results['error']}")

def run_parameter_sensitivity_analysis():
    """
    运行参数敏感性分析
    """
    print("\n=== 参数敏感性分析 ===\n")
    
    # 创建基础数据
    input_data, nt, nx = create_sample_data()
    
    # 基础参数
    base_params = {
        'dx': 100.0,
        'dt': 1.0,
        'nx': nx,
        'nt': nt,
        'manning_n': 0.015,
        'channel_width': 15.0,
        'channel_slope': 0.001
    }
    
    # 测试不同的Manning粗糙系数
    manning_values = [0.010, 0.015, 0.020, 0.025]
    results_comparison = {}
    
    print("测试不同Manning粗糙系数的影响:")
    for manning_n in manning_values:
        print(f"\n  Manning系数: {manning_n}")
        
        # 更新参数
        test_params = base_params.copy()
        test_params['manning_n'] = manning_n
        
        # 运行模型
        model = SaintVenantModel()
        results = model.run(input_data, test_params)
        
        if results['success']:
            # 计算关键指标
            max_depth = np.max(results['water_depth'])
            max_velocity = np.max(results['velocity'])
            max_discharge = np.max(results['discharge'])
            
            print(f"    最大水深: {max_depth:.3f} m")
            print(f"    最大流速: {max_velocity:.3f} m/s")
            print(f"    最大流量: {max_discharge:.3f} m³/s")
            
            results_comparison[manning_n] = {
                'max_depth': max_depth,
                'max_velocity': max_velocity,
                'max_discharge': max_discharge
            }
        else:
            print(f"    运行失败: {results['message']}")
    
    # 绘制敏感性分析结果
    if results_comparison:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle('Manning粗糙系数敏感性分析', fontsize=16)
        
        manning_list = list(results_comparison.keys())
        
        # 最大水深
        max_depths = [results_comparison[n]['max_depth'] for n in manning_list]
        axes[0].plot(manning_list, max_depths, 'o-', linewidth=2, markersize=8)
        axes[0].set_xlabel('Manning粗糙系数')
        axes[0].set_ylabel('最大水深 (m)')
        axes[0].set_title('最大水深 vs Manning系数')
        axes[0].grid(True)
        
        # 最大流速
        max_velocities = [results_comparison[n]['max_velocity'] for n in manning_list]
        axes[1].plot(manning_list, max_velocities, 's-', linewidth=2, markersize=8)
        axes[1].set_xlabel('Manning粗糙系数')
        axes[1].set_ylabel('最大流速 (m/s)')
        axes[1].set_title('最大流速 vs Manning系数')
        axes[1].grid(True)
        
        # 最大流量
        max_discharges = [results_comparison[n]['max_discharge'] for n in manning_list]
        axes[2].plot(manning_list, max_discharges, '^-', linewidth=2, markersize=8)
        axes[2].set_xlabel('Manning粗糙系数')
        axes[2].set_ylabel('最大流量 (m³/s)')
        axes[2].set_title('最大流量 vs Manning系数')
        axes[2].grid(True)
        
        plt.tight_layout()
        plt.savefig("saint_venant_sensitivity.png", dpi=300, bbox_inches='tight')
        plt.show()

if __name__ == "__main__":
    try:
        # 运行基本示例
        run_saint_venant_example()
        
        # 运行敏感性分析
        run_parameter_sensitivity_analysis()
        
    except Exception as e:
        print(f"示例运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
