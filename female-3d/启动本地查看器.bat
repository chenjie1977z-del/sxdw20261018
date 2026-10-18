@echo off
chcp 65001 >nul
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 "%~dp0start_viewer.py"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo 未找到 Python 3。单独查看可直接打开 female-3d.html。
    echo 在 Obsidian 中嵌入交互网页需要先安装 Python 3，再重新运行本文件。
  ) else (
    python "%~dp0start_viewer.py"
  )
)
pause
