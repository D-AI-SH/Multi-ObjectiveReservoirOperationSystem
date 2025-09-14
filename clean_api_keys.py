#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥清理脚本
在打包前清理配置文件中的敏感信息
"""

import json
import shutil
from pathlib import Path

def clean_api_keys():
    """清理API密钥配置文件"""
    config_file = Path("config/api_keys.json")
    
    if not config_file.exists():
        print("API密钥配置文件不存在，跳过清理")
        return
    
    # 备份原文件
    backup_file = config_file.with_suffix('.json.backup')
    shutil.copy2(config_file, backup_file)
    print(f"已备份原配置文件到: {backup_file}")
    
    # 读取配置文件
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 清理所有API密钥
    cleaned_config = {}
    for vendor, settings in config.items():
        if vendor == "_meta":
            cleaned_config[vendor] = settings
            continue
            
        cleaned_settings = {}
        for key, value in settings.items():
            if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                cleaned_settings[key] = ""  # 清空敏感信息
            else:
                cleaned_settings[key] = value
        
        cleaned_config[vendor] = cleaned_settings
    
    # 保存清理后的配置
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_config, f, ensure_ascii=False, indent=2)
    
    print("已清理API密钥配置文件")
    print("清理后的配置:")
    for vendor, settings in cleaned_config.items():
        if vendor != "_meta":
            print(f"  {vendor}: API密钥已清空")

def restore_api_keys():
    """恢复API密钥配置文件"""
    config_file = Path("config/api_keys.json")
    backup_file = config_file.with_suffix('.json.backup')
    
    if backup_file.exists():
        shutil.copy2(backup_file, config_file)
        print("已恢复API密钥配置文件")
    else:
        print("未找到备份文件，无法恢复")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_api_keys()
    else:
        clean_api_keys()
