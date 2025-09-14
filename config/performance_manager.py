"""
AI助手性能配置管理器
用于读取和应用性能优化配置
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import time


class PerformanceManager:
    """AI助手性能配置管理器"""
    
    def __init__(self, config_file: str = "ai_performance_config_commented.json"):
        """
        初始化性能管理器
        
        Args:
            config_file: 配置文件路径，默认使用带注释的配置文件
        """
        self.config_dir = Path(__file__).parent
        self.config_file = self.config_dir / config_file
        self.config = self._load_config()
        self.cache = {}  # 简单的内存缓存
        self.cache_hits = 0
        self.cache_misses = 0
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"[性能配置] 成功加载配置文件: {self.config_file}")
                return config
            else:
                print(f"[性能配置] 配置文件不存在: {self.config_file}")
                return self._get_default_config()
        except Exception as e:
            print(f"[性能配置] 加载配置文件失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "performance_settings": {
                "enable_fast_mode": False,
                "enable_vector_cache": True,
                "max_cache_size": 50,
                "vector_search_k": 3,
                "similarity_threshold": 0.3,
                "enable_performance_monitoring": True,
                "stream_chunk_size": 5
            },
            "model_settings": {
                "temperature": 0.5,
                "max_tokens": 4000,
                "timeout_seconds": 45,
                "enable_mermaid_generation": True
            },
            "ui_settings": {
                "show_thinking_animation": True,
                "auto_scroll": True,
                "markdown_rendering": True
            }
        }
    
    def get_performance_setting(self, key: str, default: Any = None) -> Any:
        """获取性能设置"""
        return self.config.get("performance_settings", {}).get(key, default)
    
    def get_model_setting(self, key: str, default: Any = None) -> Any:
        """获取模型设置"""
        return self.config.get("model_settings", {}).get(key, default)
    
    def get_ui_setting(self, key: str, default: Any = None) -> Any:
        """获取UI设置"""
        return self.config.get("ui_settings", {}).get(key, default)
    
    def should_monitor_performance(self) -> bool:
        """是否启用性能监控"""
        return self.get_performance_setting("enable_performance_monitoring", True)
    
    def is_fast_mode_enabled(self) -> bool:
        """是否启用快速模式"""
        return self.get_performance_setting("enable_fast_mode", False)
    
    def is_cache_enabled(self) -> bool:
        """是否启用缓存"""
        return self.get_performance_setting("enable_vector_cache", True)
    
    def is_mermaid_generation_enabled(self) -> bool:
        """是否启用Mermaid图表生成"""
        return self.get_model_setting("enable_mermaid_generation", True)
    
    def get_cache_key(self, prompt: str) -> str:
        """生成缓存键"""
        # 简单的缓存键生成，可以根据需要优化
        return prompt.strip().lower()[:100]
    
    def get_cached_response(self, prompt: str) -> Optional[str]:
        """获取缓存的响应"""
        if not self.is_cache_enabled():
            return None
            
        cache_key = self.get_cache_key(prompt)
        if cache_key in self.cache:
            self.cache_hits += 1
            if self.should_monitor_performance():
                print(f"[性能监控] 缓存命中: {cache_key[:30]}...")
            return self.cache[cache_key]
        
        self.cache_misses += 1
        return None
    
    def cache_response(self, prompt: str, response: str) -> None:
        """缓存响应"""
        if not self.is_cache_enabled():
            return
            
        cache_key = self.get_cache_key(prompt)
        max_cache_size = self.get_performance_setting("max_cache_size", 50)
        
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= max_cache_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = response
        if self.should_monitor_performance():
            print(f"[性能监控] 缓存保存: {cache_key[:30]}...")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        print("[性能监控] 缓存已清空")
    
    def start_timer(self) -> float:
        """开始计时"""
        return time.time()
    
    def end_timer(self, start_time: float, operation: str = "操作") -> float:
        """结束计时并返回耗时"""
        elapsed = time.time() - start_time
        if self.should_monitor_performance():
            print(f"[性能监控] {operation}耗时: {elapsed:.2f}秒")
        return elapsed


# 全局性能管理器实例
performance_manager = PerformanceManager()
