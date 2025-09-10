from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def get_pareto_front(F: np.ndarray) -> np.ndarray:
    """获取帕累托前沿解的索引。"""
    from pymoo.util.function_loader import load_function

    fast_non_dominated_sort = load_function("fast_non_dominated_sort")
    fronts = fast_non_dominated_sort(F)
    return fronts[0]


def analyze_single_solution(
    x: np.ndarray,
    f: np.ndarray,
    active_objs: List[str],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """分析单个调度解的特征。"""
    Q_min = float(params.get("Q_min", 0.0))
    Q_max = float(params.get("Q_max", 1000.0))
    Q_allowed = float(params.get("Q_allowed", Q_max))
    Q_target = float(params.get("Q_target", (Q_min + Q_max) / 2))
    Q_eco = float(params.get("Q_eco", Q_min))
    Head = float(params.get("head", 50.0))

    analysis = {
        "flow_statistics": {
            "min_flow": float(np.min(x)),
            "max_flow": float(np.max(x)),
            "mean_flow": float(np.mean(x)),
            "std_flow": float(np.std(x)),
            "total_volume": float(np.sum(x)),
        },
        "constraint_satisfaction": {
            "min_flow_violation": float(np.min(x) - Q_min),
            "max_flow_violation": float(np.max(x) - Q_max),
            "flood_risk": float(np.max(x) / Q_allowed),
            "supply_deficit": float(np.sum(np.maximum(Q_target - x, 0))),
            "ecology_violation": float(np.sum(x < Q_eco)),
        },
        "performance_metrics": {
            "power_generation": float(np.sum(x * Head)),
            "supply_reliability": float(np.sum(x >= Q_target) / len(x)),
            "ecology_satisfaction": float(np.sum(x >= Q_eco) / len(x)),
        },
    }
    return analysis


def recommend_strategies(
    pareto_X: np.ndarray,
    pareto_F: np.ndarray,
    active_objs: List[str],
    reservoir_id: int,
) -> List[Dict[str, Any]]:
    """基于不同目标偏好给出推荐策略。"""
    recommendations: List[Dict[str, Any]] = []

    # 防洪优先
    if "flood" in active_objs:
        flood_idx = active_objs.index("flood")
        min_flood_idx = int(np.argmin(pareto_F[:, flood_idx]))
        recommendations.append(
            {
                "strategy_type": "flood_control_priority",
                "description": "防洪优先策略：最小化最大下泄流量",
                "solution_id": min_flood_idx + 1,
                "decision_variables": pareto_X[min_flood_idx].tolist(),
                "objective_values": pareto_F[min_flood_idx].tolist(),
            }
        )

    # 发电优先
    if "power" in active_objs:
        power_idx = active_objs.index("power")
        min_power_idx = int(np.argmin(pareto_F[:, power_idx]))
        recommendations.append(
            {
                "strategy_type": "power_generation_priority",
                "description": "发电优先策略：最大化发电量",
                "solution_id": min_power_idx + 1,
                "decision_variables": pareto_X[min_power_idx].tolist(),
                "objective_values": pareto_F[min_power_idx].tolist(),
            }
        )

    # 供水优先
    if "supply" in active_objs:
        supply_idx = active_objs.index("supply")
        min_supply_idx = int(np.argmin(pareto_F[:, supply_idx]))
        recommendations.append(
            {
                "strategy_type": "water_supply_priority",
                "description": "供水优先策略：最小化供水缺口",
                "solution_id": min_supply_idx + 1,
                "decision_variables": pareto_X[min_supply_idx].tolist(),
                "objective_values": pareto_F[min_supply_idx].tolist(),
            }
        )

    # 生态优先
    if "ecology" in active_objs:
        ecology_idx = active_objs.index("ecology")
        min_ecology_idx = int(np.argmin(pareto_F[:, ecology_idx]))
        recommendations.append(
            {
                "strategy_type": "ecology_priority",
                "description": "生态优先策略：最大化生态基流满足度",
                "solution_id": min_ecology_idx + 1,
                "decision_variables": pareto_X[min_ecology_idx].tolist(),
                "objective_values": pareto_F[min_ecology_idx].tolist(),
            }
        )

    # 平衡策略
    if len(active_objs) > 1 and len(pareto_F) > 0:
        max_values = np.max(pareto_F, axis=0)
        max_values = np.where(max_values == 0, 1.0, max_values)
        normalized_F = pareto_F / max_values
        weights = np.ones(len(active_objs)) / len(active_objs)
        weighted_sum = np.sum(normalized_F * weights, axis=1)
        balanced_idx = int(np.argmin(weighted_sum))
        recommendations.append(
            {
                "strategy_type": "balanced_strategy",
                "description": "平衡策略：综合考虑所有目标",
                "solution_id": balanced_idx + 1,
                "decision_variables": pareto_X[balanced_idx].tolist(),
                "objective_values": pareto_F[balanced_idx].tolist(),
            }
        )

    return recommendations


def build_reservoir_strategy(
    X: np.ndarray,
    F: np.ndarray,
    reservoir_id: int,
    active_objs: List[str],
    params: Dict[str, Any],
    horizon: int,
) -> Dict[str, Any]:
    """为单个水库构建调度策略信息。"""
    pareto_indices = get_pareto_front(F)
    pareto_X = X[pareto_indices]
    pareto_F = F[pareto_indices]

    strategy_info: Dict[str, Any] = {
        "reservoir_id": reservoir_id,
        "pareto_solutions_count": int(len(pareto_indices)),
        "total_solutions": int(len(X)),
        "horizon": horizon,
        "objectives": active_objs,
        "pareto_solutions": [],
        "recommended_strategies": [],
    }

    for i, (x, f) in enumerate(zip(pareto_X, pareto_F)):
        solution = {
            "solution_id": i + 1,
            "decision_variables": x.tolist(),
            "objective_values": f.tolist(),
            "objective_dict": dict(zip(active_objs, f)),
            "analysis": analyze_single_solution(x, f, active_objs, params),
        }
        strategy_info["pareto_solutions"].append(solution)

    strategy_info["recommended_strategies"] = recommend_strategies(
        pareto_X, pareto_F, active_objs, reservoir_id
    )

    return strategy_info


def analyze_cross_reservoir_coordination(
    all_strategies: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if len(all_strategies) <= 1:
        return {"message": "单水库系统，无需协调分析"}

    coordination_analysis: Dict[str, Any] = {
        "coordination_opportunities": [],
        "potential_conflicts": [],
        "recommended_coordination_strategies": [],
    }

    for i, strategy1 in enumerate(all_strategies):
        for j, strategy2 in enumerate(all_strategies[i + 1 :], i + 1):
            res1_id = strategy1["reservoir_id"]
            res2_id = strategy2["reservoir_id"]
            coordination_analysis["coordination_opportunities"].append(
                {
                    "reservoir_pair": f"{res1_id}-{res2_id}",
                    "analysis": f"水库{res1_id}和水库{res2_id}的协调调度分析",
                }
            )

    return coordination_analysis


def generate_implementation_guidance(
    all_strategies: List[Dict[str, Any]], params: Dict[str, Any]
) -> Dict[str, Any]:
    guidance: Dict[str, Any] = {
        "operational_recommendations": [],
        "monitoring_requirements": [],
        "adjustment_criteria": [],
    }

    for strategy in all_strategies:
        res_id = strategy["reservoir_id"]
        guidance["operational_recommendations"].append(
            {
                "reservoir_id": res_id,
                "recommendations": [
                    f"水库{res_id}建议采用平衡策略进行日常调度",
                    f"在汛期优先考虑防洪策略",
                    f"在枯水期优先考虑供水策略",
                ],
            }
        )
        guidance["monitoring_requirements"].append(
            {
                "reservoir_id": res_id,
                "requirements": [
                    "实时监测水库水位和下泄流量",
                    "监测下游河道流量和水质",
                    "监测发电效率和供水可靠性",
                ],
            }
        )
        guidance["adjustment_criteria"].append(
            {
                "reservoir_id": res_id,
                "criteria": [
                    "当防洪风险超过阈值时调整调度策略",
                    "当供水缺口超过10%时启动应急调度",
                    "当生态基流不满足时优先保障生态需求",
                ],
            }
        )

    return guidance


def build_comprehensive_strategy_report(
    all_strategies: List[Dict[str, Any]],
    reservoir_count: int,
    active_objs: List[str],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    report = {
        "summary": {
            "total_reservoirs": reservoir_count,
            "active_objectives": active_objs,
            "optimization_parameters": params,
            "total_pareto_solutions": sum(
                len(s["pareto_solutions"]) for s in all_strategies
            ),
        },
        "reservoir_strategies": all_strategies,
        "cross_reservoir_analysis": analyze_cross_reservoir_coordination(all_strategies),
        "implementation_guidance": generate_implementation_guidance(all_strategies, params),
    }
    return report


