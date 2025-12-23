@echo off
chcp 65001 >nul

echo 开始打包应用...

:: 清理旧的构建文件
if exist build rmdir /s /q build
if exist output rmdir /s /q output

:: 创建输出目录
mkdir output\auto_subtitle

:: 复制 icon 文件夹到输出目录
echo 正在复制 icon 文件夹...
xcopy /s /e /i /y icon output\auto_subtitle\icon

:: 复制配置文件到输出目录
echo 正在复制配置文件...
copy .config.yaml output\auto_subtitle\
copy README.md output\auto_subtitle\
copy LICENSE output\auto_subtitle\

:: 使用 pyinstaller 打包，直接输出到指定目录
echo 正在执行 pyinstaller...
pyinstaller --onefile --windowed --name auto_subtitle --icon icon\icon.ico --distpath output\auto_subtitle --workpath build main.py

if errorlevel 1 (
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo 打包完成！输出目录: output\auto_subtitle
pause
