@echo off
chcp 65001 > nul
echo =====================================================================
echo  BIÊN DỊCH BÁO CÁO BÀI TẬP LỚN BẰNG XELATEX (CHUẨN UET)
echo  Đề tài: Nghiên cứu TiDB vs MySQL (Phần A - Phần B)
echo =====================================================================

where xelatex >nul 2>nul
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy lệnh 'xelatex' trong hệ thống PATH!
    echo Vui lòng cài đặt TeX Live hoặc MiKTeX, hoặc tải thư mục này lên Overleaf.
    pause
    exit /b 1
)

echo [1/2] Đang chạy XeLaTeX lần 1 (Thu thập mục lục và nhãn)...
xelatex -synctex=1 -interaction=nonstopmode main.tex

echo [2/2] Đang chạy XeLaTeX lần 2 (Đồng bộ số trang và tham chiếu chéo)...
xelatex -synctex=1 -interaction=nonstopmode main.tex

if exist main.pdf (
    echo =====================================================================
    echo [THÀNH CÔNG] File 'main.pdf' đã được tạo thành công!
    echo =====================================================================
) else (
    echo [CẢNH BÁO] Kiểm tra file main.log để xem chi tiết lỗi biên dịch.
)

pause
