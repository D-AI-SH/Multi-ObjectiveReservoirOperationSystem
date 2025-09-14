#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包调试脚本
帮助定位打包过程中的问题
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_environment():
    """检查Python环境"""
    print("=" * 50)
    print("Python环境检查")
    print("=" * 50)
    
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查conda环境
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '未设置')
    print(f"Conda环境: {conda_env}")
    
    return True

def check_pyinstaller():
    """检查PyInstaller"""
    print("\n" + "=" * 50)
    print("PyInstaller检查")
    print("=" * 50)
    
    try:
        import PyInstaller
        print(f"✓ PyInstaller版本: {PyInstaller.__version__}")
        
        # 检查pyinstaller命令
        try:
            result = subprocess.run(['pyinstaller', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"✓ PyInstaller命令可用: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"✗ PyInstaller命令不可用: {e}")
            return False
            
    except ImportError:
        print("✗ PyInstaller未安装")
        print("请运行: pip install pyinstaller")
        return False
    
    return True

def check_dependencies():
    """检查依赖包"""
    print("\n" + "=" * 50)
    print("依赖包检查")
    print("=" * 50)
    
    required_packages = [
        'PyQt6', 'pandas', 'numpy', 'matplotlib', 
        'sentence_transformers', 'faiss', 'pymoo'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            module = __import__(package)
            version = getattr(module, '__version__', '未知版本')
            print(f"✓ {package}: {version}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package}: 未安装")
    
    if missing_packages:
        print(f"\n缺少的包: {', '.join(missing_packages)}")
        return False
    
    return True

def check_project_files():
    """检查项目文件"""
    print("\n" + "=" * 50)
    print("项目文件检查")
    print("=" * 50)
    
    required_files = [
        'mainLAYER/main.py',
        'build_config.spec',
        'version_info.txt',
        'clean_api_keys.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✓ {file_path} ({size} bytes)")
        else:
            missing_files.append(file_path)
            print(f"✗ {file_path}: 不存在")
    
    if missing_files:
        print(f"\n缺少的文件: {', '.join(missing_files)}")
        return False
    
    return True

def test_simple_pyinstaller():
    """测试简单的PyInstaller命令"""
    print("\n" + "=" * 50)
    print("PyInstaller简单测试")
    print("=" * 50)
    
    # 创建简单的测试脚本
    test_script = "test_simple.py"
    with open(test_script, 'w', encoding='utf-8') as f:
        f.write("""
#!/usr/bin/env python3
print("Hello, PyInstaller!")
""")
    
    try:
        # 测试pyinstaller命令
        cmd = ['pyinstaller', '--onefile', '--name', 'test_app', test_script]
        print(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✓ PyInstaller基本功能正常")
            return True
        else:
            print(f"✗ PyInstaller测试失败")
            print(f"返回码: {result.returncode}")
            print(f"错误输出: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ PyInstaller测试超时")
        return False
    except Exception as e:
        print(f"✗ PyInstaller测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        for file in [test_script, 'test_app.spec']:
            if os.path.exists(file):
                os.remove(file)
        
        # 清理构建目录
        for dir_name in ['build', 'dist']:
            if os.path.exists(dir_name):
                import shutil
                shutil.rmtree(dir_name)

def main():
    """主函数"""
    print("多目标水库调度系统打包调试工具")
    
    checks = [
        ("Python环境", check_python_environment),
        ("PyInstaller", check_pyinstaller),
        ("依赖包", check_dependencies),
        ("项目文件", check_project_files),
        ("PyInstaller测试", test_simple_pyinstaller)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name}检查异常: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 50)
    print("检查结果总结")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有检查都通过，可以尝试打包!")
    else:
        print("\n⚠️ 存在问题，请先解决上述问题再尝试打包")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n用户中断调试")
        sys.exit(1)
    except Exception as e:
        print(f"\n调试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
