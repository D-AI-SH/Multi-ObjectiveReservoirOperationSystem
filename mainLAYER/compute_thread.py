"""
计算线程模块
负责在独立线程中执行模型计算和调度优化，避免阻塞主UI线程
"""

import sys
import os
from typing import Dict, Any, Optional, Callable
from PyQt6.QtCore import QThread, QObject, pyqtSignal
import traceback

# 动态添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from modelLAYER.model_manager import ModelManager
from scheduleLAYER.schedule_manager import ScheduleManager


class ComputeWorker(QObject):
    """
    计算工作器，在独立线程中执行计算任务
    """
    
    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态消息
    model_completed = pyqtSignal(dict, dict)  # 模型结果, 失败信息
    schedule_completed = pyqtSignal(dict)  # 调度结果
    error_occurred = pyqtSignal(str, str)  # 错误类型, 错误消息
    task_finished = pyqtSignal()  # 任务完成信号
    
    def __init__(self):
        super().__init__()
        self.model_manager = ModelManager()
        self.schedule_manager = ScheduleManager()
        self._is_cancelled = False
        
    def cancel_task(self):
        """取消当前任务"""
        self._is_cancelled = True
        
    def run_model_computation(self, selected_model: str, reservoir_input_data: Dict, 
                            params: Dict[str, Any], required_ids: list):
        """
        运行模型计算
        
        Args:
            selected_model: 选择的模型名称
            reservoir_input_data: 多水库输入数据
            params: 模型参数
            required_ids: 所需数据ID列表
        """
        try:
            self._is_cancelled = False
            self.progress_updated.emit(0, "开始模型计算...")
            
            # 选择模型
            self.model_manager.select_model(selected_model)
            self.progress_updated.emit(10, f"已选择模型: {selected_model}")
            
            if self._is_cancelled:
                return
                
            # 为每个水库运行模型
            reservoir_results = {}
            failures = {}
            total_reservoirs = len(reservoir_input_data)
            
            for i, (reservoir_id, input_df) in enumerate(reservoir_input_data.items()):
                if self._is_cancelled:
                    return
                    
                progress = 10 + int((i / total_reservoirs) * 80)
                self.progress_updated.emit(progress, f"正在为水库 {reservoir_id} 运行模型...")
                
                try:
                    results_df = self.model_manager.run_model(input_df, params)
                    if results_df is not None:
                        reservoir_results[reservoir_id] = results_df
                        print(f"水库 {reservoir_id} 模型运行完成")
                    else:
                        # 从模型管理器提取失败原因
                        last_raw = getattr(self.model_manager, 'results', None)
                        if isinstance(last_raw, dict) and not last_raw.get('success', True):
                            failures[reservoir_id] = {
                                'message': last_raw.get('message', '未知错误'),
                                'error': last_raw.get('error'),
                                'diagnostics': last_raw.get('diagnostics', {})
                            }
                        else:
                            failures[reservoir_id] = {'message': '运行失败（未提供详细错误）'}
                            
                except Exception as e:
                    failures[reservoir_id] = {
                        'message': f'模型运行异常: {str(e)}',
                        'error': str(e),
                        'diagnostics': {'traceback': traceback.format_exc()}
                    }
                    print(f"水库 {reservoir_id} 模型运行异常: {e}")
            
            if self._is_cancelled:
                return
                
            self.progress_updated.emit(95, "模型计算完成，准备结果...")
            
            # 发送结果
            self.model_completed.emit(reservoir_results, failures)
            self.progress_updated.emit(100, "模型计算完成")
            
        except Exception as e:
            error_msg = f"模型计算过程中发生错误: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            self.error_occurred.emit("model_computation", error_msg)
        finally:
            self.task_finished.emit()
    
    def run_schedule_optimization(self, objectives: Dict[str, bool], params: Dict[str, Any], 
                                schedule_input: Dict[str, Any]):
        """
        运行调度优化计算
        
        Args:
            objectives: 优化目标
            params: 调度参数
            schedule_input: 调度输入数据
        """
        try:
            self._is_cancelled = False
            self.progress_updated.emit(0, "开始调度优化...")
            
            if self._is_cancelled:
                return
                
            self.progress_updated.emit(20, "初始化优化算法...")
            
            # 运行调度优化
            results_df = self.schedule_manager.optimize(schedule_input, objectives, params)
            
            if self._is_cancelled:
                return
                
            self.progress_updated.emit(80, "优化计算完成，处理结果...")
            
            if results_df is not None and not results_df.empty:
                print("调度优化结果:\n", results_df.head())
                
                # 获取调度策略信息
                schedule_strategy = results_df.attrs.get('schedule_strategy', {})
                
                # 构建调度结果
                import pandas as pd
                
                # 修复目标函数数据结构，确保包含reservoir_id字段
                objectives_df = results_df[['flood', 'power', 'supply', 'ecology', 'reservoir_id']].copy()
                
                # 添加帕累托前沿数据
                pareto_front = results_df.copy()
                
                schedule_results = {
                    'optimization_results': results_df,
                    'objectives': objectives_df,
                    'pareto_front': pareto_front,
                    'schedule_strategy': schedule_strategy
                }
                
                self.progress_updated.emit(95, "调度优化完成，准备结果...")
                
                # 发送结果
                self.schedule_completed.emit(schedule_results)
                self.progress_updated.emit(100, "调度优化完成")
                
            else:
                self.error_occurred.emit("schedule_optimization", "调度优化失败或无结果")
                
        except Exception as e:
            error_msg = f"调度优化过程中发生错误: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            self.error_occurred.emit("schedule_optimization", error_msg)
        finally:
            self.task_finished.emit()


class ComputeThread(QThread):
    """
    计算线程管理器
    """
    
    # 定义信号
    progress_updated = pyqtSignal(int, str)
    model_completed = pyqtSignal(dict, dict)
    schedule_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str, str)
    task_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = ComputeWorker()
        self.worker.moveToThread(self)
        
        # 连接worker信号到线程信号
        self.worker.progress_updated.connect(self.progress_updated)
        self.worker.model_completed.connect(self.model_completed)
        self.worker.schedule_completed.connect(self.schedule_completed)
        self.worker.error_occurred.connect(self.error_occurred)
        self.worker.task_finished.connect(self.task_finished)
        
        # 存储任务参数
        self._current_task = None
        self._task_params = None
        
    def run(self):
        """线程运行方法"""
        if self._current_task == 'model':
            self.worker.run_model_computation(*self._task_params)
        elif self._current_task == 'schedule':
            self.worker.run_schedule_optimization(*self._task_params)
        
    def run_model_computation(self, selected_model: str, reservoir_input_data: Dict, 
                            params: Dict[str, Any], required_ids: list):
        """启动模型计算任务"""
        if self.isRunning():
            print("警告：计算线程正在运行中，请等待当前任务完成")
            return False
            
        self._current_task = 'model'
        self._task_params = (selected_model, reservoir_input_data, params, required_ids)
        self.start()
        return True
        
    def run_schedule_optimization(self, objectives: Dict[str, bool], params: Dict[str, Any], 
                                schedule_input: Dict[str, Any]):
        """启动调度优化任务"""
        if self.isRunning():
            print("警告：计算线程正在运行中，请等待当前任务完成")
            return False
            
        self._current_task = 'schedule'
        self._task_params = (objectives, params, schedule_input)
        self.start()
        return True
        
    def cancel_current_task(self):
        """取消当前任务"""
        self.worker.cancel_task()
        
    def is_busy(self) -> bool:
        """检查线程是否忙碌"""
        return self.isRunning()
