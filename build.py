#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多目标水库调度系统打包脚本
使用PyInstaller将项目打包成可执行文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_environment():
    """检查打包环境"""
    print("检查打包环境...")
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("警告: 建议使用Python 3.8或更高版本")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("错误: 未安装PyInstaller")
        print("请运行: pip install pyinstaller")
        return False
    
    # 检查主要依赖
    required_packages = [
        'PyQt6', 'pandas', 'numpy', 'matplotlib', 
        'sentence_transformers', 'faiss', 'pymoo'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (缺失)")
    
    if missing_packages:
        print(f"错误: 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def prepare_build():
    """准备构建环境"""
    print("准备构建环境...")
    
    # 清理API密钥
    print("清理API密钥...")
    try:
        result = subprocess.run([sys.executable, 'clean_api_keys.py'], 
                              check=True, capture_output=True, text=True)
        print("API密钥清理成功")
    except subprocess.CalledProcessError as e:
        print(f"API密钥清理失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("警告: clean_api_keys.py 文件不存在，跳过API密钥清理")
    
    # 检查必要文件
    required_files = [
        'mainLAYER/main.py',
        'build_config.spec',
        'version_info.txt'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"错误: 缺少必要文件 {file_path}")
            return False
        else:
            print(f"✓ 找到文件: {file_path}")
    
    return True

def build_executable():
    """构建可执行文件"""
    print("开始构建可执行文件...")
    
    # 使用spec文件构建
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'build_config.spec'
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        # 不捕获输出，让用户看到实时进度
        result = subprocess.run(cmd, check=True)
        print("构建成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"返回码: {e.returncode}")
        return False
    except FileNotFoundError:
        print("错误: 找不到 pyinstaller 命令")
        print("请确保已安装 PyInstaller: pip install pyinstaller")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("多目标水库调度系统打包工具")
    print("=" * 60)
    
    try:
        # 检查环境
        print("\n步骤 1: 检查环境")
        if not check_environment():
            print("❌ 环境检查失败，退出打包")
            return False
        print("✅ 环境检查通过")
        
        
        # 准备构建
        print("\n步骤 3: 准备构建环境")
        if not prepare_build():
            print("❌ 构建准备失败，退出打包")
            return False
        print("✅ 构建环境准备完成")
        
        # 构建可执行文件
        print("\n步骤 4: 构建可执行文件")
        if not build_executable():
            print("❌ 构建失败")
            return False
        print("✅ 可执行文件构建完成")
        
        
        print("\n" + "=" * 60)
        print("🎉 打包完成!")
        print("可执行文件位置: dist/多目标水库调度系统.exe")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 打包过程中发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ 打包成功完成!")
            sys.exit(0)
        else:
            print("\n❌ 打包失败!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断打包")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 打包过程中发生严重错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
