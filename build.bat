@echo off
chcp 65001
echo 开始构建多目标水库调度系统...

REM 激活conda环境
call conda activate hydro

REM 检查PyInstaller是否安装
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller
)

REM 清理之前的构建
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 运行构建
echo 开始打包...
pyinstaller --clean "多目标水库调度系统.spec"

if errorlevel 1 (
    echo 构建失败！
    pause
    exit /b 1
)

echo 构建完成！
echo 可执行文件位置: dist\多目标水库调度系统.exe
echo.
echo 注意：首次运行需要配置API密钥
echo 请将config/api_keys.json文件复制到可执行文件同目录下
echo 并填入您的API密钥信息
echo.
pause
