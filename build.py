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

def clean_build_dirs():
    """清理构建目录"""
    print("清理构建目录...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已删除: {dir_name}")
    
    # 清理.spec文件
    spec_files = list(Path('.').glob('*.spec'))
    for spec_file in spec_files:
        if spec_file.name != 'build_config.spec':
            spec_file.unlink()
            print(f"已删除: {spec_file}")

def prepare_build():
    """准备构建环境"""
    print("准备构建环境...")
    
    # 清理API密钥
    print("清理API密钥...")
    subprocess.run([sys.executable, 'clean_api_keys.py'], check=True)
    
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
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def post_build_cleanup():
    """构建后清理"""
    print("执行构建后清理...")
    
    # 恢复API密钥
    print("恢复API密钥...")
    subprocess.run([sys.executable, 'clean_api_keys.py', 'restore'], check=True)
    
    # 清理临时文件
    temp_files = ['clean_api_keys.py', 'build_config.spec', 'version_info.txt']
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"已删除临时文件: {temp_file}")

def main():
    """主函数"""
    print("=" * 60)
    print("多目标水库调度系统打包工具")
    print("=" * 60)
    
    # 检查环境
    if not check_environment():
        print("环境检查失败，退出打包")
        return False
    
    # 清理构建目录
    clean_build_dirs()
    
    # 准备构建
    if not prepare_build():
        print("构建准备失败，退出打包")
        return False
    
    # 构建可执行文件
    if not build_executable():
        print("构建失败")
        return False
    
    # 构建后清理
    post_build_cleanup()
    
    print("=" * 60)
    print("打包完成!")
    print("可执行文件位置: dist/多目标水库调度系统.exe")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n用户中断打包")
        sys.exit(1)
    except Exception as e:
        print(f"打包过程中发生错误: {e}")
        sys.exit(1)
