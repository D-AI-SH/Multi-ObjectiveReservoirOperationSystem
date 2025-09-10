from __future__ import annotations

"""schedule_manager.py
基于 `pymoo` 的 NSGA-III 多目标调度优化实现。

核心假设（后续可替换为真实水库调度模型）
------------------------------------------------
• 决策变量：给定时间步长内的下泄流量序列 :math:`Q_t` (单位 m³/s)。
• 目标函数  (均为 **最小化** 形式)：
  1. 防洪目标 (flood)  ——  最大下泄流量占允许值的比例 (越小越好)。
  2. 发电目标 (power)  ——  负的累计下泄流量 (即最大化发电量)。
  3. 供水目标 (supply) ——  供水缺口比例 (越小越好)。
  4. 生态目标 (ecology) ——  不满足生态基流的时段比例 (越小越好)。

如需结合真实水文、水动力模型，只需替换 `_evaluate` 方法即可。
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from .strategy import (
    build_reservoir_strategy,
    build_comprehensive_strategy_report,
)

# ----------------------------------------------------------------------
# 依赖检查
# ----------------------------------------------------------------------
try:
    from pymoo.core.problem import Problem  # type: ignore
    from pymoo.util.ref_dirs import get_reference_directions  # type: ignore
    from pymoo.algorithms.moo.nsga3 import NSGA3  # type: ignore
    from pymoo.optimize import minimize  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        "未找到 pymoo 库，请先执行 `pip install pymoo` 后再运行调度优化。"
    ) from exc


class _ReservoirSchedulingProblem(Problem):
    """基于给定参数的自定义多目标优化问题。"""

    def __init__(
        self,
        n_var: int,
        active_objs: List[str],
        Q_min: float,
        Q_max: float,
        params: Dict[str, Any],
    ) -> None:
        self.active_objs = active_objs
        self.Q_min = Q_min
        self.Q_max = Q_max
        # 允许的最大下泄流量 (防洪指标归一化)
        self.Q_allowed = float(params.get("Q_allowed", Q_max))
        # 供水目标下游需水量 (m³/s)
        self.Q_target = float(params.get("Q_target", (Q_min + Q_max) / 2))
        # 生态基流约束 (m³/s)
        self.Q_eco = float(params.get("Q_eco", Q_min))
        # 简化的水头 (用于发电量评估)
        self.Head = float(params.get("head", 50.0))
        super().__init__(n_var=n_var, n_obj=len(active_objs), n_constr=0, xl=Q_min, xu=Q_max)

    # ------------------------------------------------------------------
    # 目标函数计算
    # ------------------------------------------------------------------
    def _evaluate(self, X: np.ndarray, out: Dict, *args, **kwargs):  # type: ignore[override]
        # X 形状: (pop_size, n_var)
        pop_size = X.shape[0]
        F = np.zeros((pop_size, len(self.active_objs)))

        # ------------------------------------------------------------------
        # 各目标计算
        # ------------------------------------------------------------------
        for i, obj in enumerate(self.active_objs):
            if obj == "flood":
                # 最大下泄流量占允许值比例
                F[:, i] = np.max(X, axis=1) / self.Q_allowed
            elif obj == "power":
                # 发电量 ~ sum(Q_t * Head)；取负值进行最小化
                total_energy = np.sum(X * self.Head, axis=1)
                F[:, i] = -total_energy
            elif obj == "supply":
                # 供水缺口比例
                deficit = np.maximum(self.Q_target - X, 0.0)
                F[:, i] = np.sum(deficit, axis=1) / (self.Q_target * self.n_var)
            elif obj == "ecology":
                # 不满足生态基流的时段比例
                unsatisfied = (X < self.Q_eco).sum(axis=1)
                F[:, i] = unsatisfied / self.n_var
            else:
                raise ValueError(f"未知目标: {obj}")

        out["F"] = F


class ScheduleManager:
    """多目标调度优化管理器 (NSGA-III)。"""

    def __init__(self) -> None:
        self.results: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def optimize(
        self,
        data: Any | None,
        objectives: Dict[str, bool],
        params: Dict[str, Any],
    ) -> pd.DataFrame | None:
        """执行 NSGA-III 多目标优化。

        参数
        ------
        data
            预留接口，可传入水文/气象数据用于更精确的目标函数。
        objectives
            各目标是否启用，如 ``{"flood": True, "power": False, ...}``。
        params
            算法与领域参数，支持：
                population_size, iterations, reference_points,
                Q_min, Q_max, Q_allowed, Q_target, Q_eco, head, horizon 等。
        """
        # -------------------- 1. 处理目标 --------------------
        active_objs = [k for k, enabled in objectives.items() if enabled]
        if not active_objs:
            print("警告：未选择任何优化目标，已跳过优化。")
            return None

        # -------------------- 2. 基本参数 --------------------
        pop_size = int(params.get("population_size", 100))
        n_gen = int(params.get("iterations", 100))
        n_ref = int(params.get("reference_points", 12))
        horizon = int(params.get("horizon", 24))  # 决策时间步个数

        Q_min = float(params.get("Q_min", 0.0))
        Q_max = float(params.get("Q_max", 1000.0))

        # -------------------- 3. 多水库处理 --------------------
        # 检查是否有模型结果数据，用于确定水库数量
        reservoir_count = 1  # 默认单水库
        if data and isinstance(data, dict) and 'model_results' in data:
            reservoir_count = len(data['model_results'])
            print(f"检测到 {reservoir_count} 个水库的模型结果")

        # -------------------- 4. 为每个水库执行优化 --------------------
        all_results = []
        all_strategies = []
        
        for reservoir_id in range(1, reservoir_count + 1):
            print(f"正在为水库 {reservoir_id} 执行调度优化...")
            
            # 为每个水库创建问题实例
            problem = _ReservoirSchedulingProblem(
                n_var=horizon,
                active_objs=active_objs,
                Q_min=Q_min,
                Q_max=Q_max,
                params=params,
            )

            # 算法配置 (NSGA-III)
            ref_dirs = get_reference_directions("das-dennis", len(active_objs), n_partitions=n_ref)
            algorithm = NSGA3(pop_size=pop_size, ref_dirs=ref_dirs)

            # 运行优化
            res = minimize(problem, algorithm, ("n_gen", n_gen), seed=reservoir_id, verbose=False)

            if res is not None and res.pop is not None:
                F = res.pop.get("F")
                X = res.pop.get("X")  # 获取决策变量（调度策略）
                if F is not None and X is not None:
                    # 为每个水库创建结果DataFrame
                    df = pd.DataFrame(F, columns=active_objs)
                    # 添加水库ID列
                    df['reservoir_id'] = reservoir_id
                    # 添加时间步列
                    df['time_step'] = range(len(df))
                    all_results.append(df)
                    
                    # 生成调度策略信息（使用拆分后的策略模块）
                    strategy_info = build_reservoir_strategy(
                        X, F, reservoir_id, active_objs, params, horizon
                    )
                    all_strategies.append(strategy_info)
                    
                    print(f"水库 {reservoir_id} 优化完成")
                else:
                    print(f"水库 {reservoir_id} 优化失败")
            else:
                print(f"水库 {reservoir_id} 优化失败")

        # -------------------- 5. 合并所有水库结果 --------------------
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            self.results = combined_df
            
            # 生成综合调度策略报告（使用拆分后的策略模块）
            strategy_report = build_comprehensive_strategy_report(
                all_strategies, reservoir_count, active_objs, params
            )
            
            # 将策略报告添加到结果中
            combined_df.attrs['schedule_strategy'] = strategy_report
            
            print(f"多水库调度优化完成，共 {len(all_results)} 个水库")
            print("调度策略报告已生成")
            return combined_df
        else:
            print("所有水库优化均失败")
            return None

    # 以下策略相关逻辑已拆分到 scheduleLAYER/strategy.py
