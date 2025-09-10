#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件管理器
统一管理系统中所有配置文件的访问和操作
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self):
        # 获取项目根目录
        self.root_dir = Path(__file__).parent.parent
        self.config_dir = self.root_dir / "config"
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.data_links_config = self.config_dir / "data_links_config.json"
        self.api_keys_config = self.config_dir / "api_keys.json"
        
        # 初始化配置文件
        self._init_config_files()
    
    def _init_config_files(self):
        """初始化配置文件"""
        # 初始化数据链接配置
        if not self.data_links_config.exists():
            default_data_links = {
                "data_links": {},
                "reservoir_count": 0,
                "last_model": "",
                "auto_config_enabled": True
            }
            self.save_data_links_config(default_data_links)
        
        # 初始化API密钥配置
        if not self.api_keys_config.exists():
            default_api_keys = {
                "openai_api_key": "",
                "database_connection": "",
                "other_services": {}
            }
            self.save_api_keys_config(default_api_keys)
    
    def load_data_links_config(self) -> Dict[str, Any]:
        """加载数据链接配置"""
        try:
            if self.data_links_config.exists():
                with open(self.data_links_config, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载数据链接配置失败: {e}")
            return {}
    
    def save_data_links_config(self, config: Dict[str, Any]) -> bool:
        """保存数据链接配置"""
        try:
            with open(self.data_links_config, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存数据链接配置失败: {e}")
            return False
    
    def load_api_keys_config(self) -> Dict[str, Any]:
        """加载API密钥配置"""
        try:
            if self.api_keys_config.exists():
                with open(self.api_keys_config, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载API密钥配置失败: {e}")
            return {}
    
    def save_api_keys_config(self, config: Dict[str, Any]) -> bool:
        """保存API密钥配置"""
        try:
            with open(self.api_keys_config, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存API密钥配置失败: {e}")
            return False
    
    def get_config_path(self, config_name: str) -> Path:
        """获取配置文件路径"""
        return self.config_dir / config_name
    
    def get_config_dir(self) -> Path:
        """获取配置目录路径"""
        return self.config_dir
    
    def list_config_files(self) -> list:
        """列出所有配置文件"""
        config_files = []
        for file_path in self.config_dir.glob("*.json"):
            config_files.append(file_path.name)
        return config_files

# 全局配置管理器实例
config_manager = ConfigManager()

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    return config_manager
