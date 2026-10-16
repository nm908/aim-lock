# ADB Easy Installer cho Windows

Ứng dụng Windows tiếng Việt giúp cài APK từ PC vào Android qua ADB, xem danh sách ứng dụng người dùng và gỡ ứng dụng đã chọn sau khi xác nhận.

## Tải bản dùng ngay
Sau khi bản build hoàn thành, tải ADBEasyInstaller.exe tại:
https://github.com/nm908/aim-lock/releases/tag/adb-easy-installer-v1

Bản EXE kèm Android SDK Platform-Tools chính thức. Không cần cài Android Studio hoặc Python để chạy bản EXE.

## Cách dùng
1. Trên điện thoại, bật Tùy chọn nhà phát triển và Gỡ lỗi USB.
2. Kết nối điện thoại với PC bằng cáp USB có hỗ trợ truyền dữ liệu; mở khóa màn hình.
3. Chấp nhận lời nhắc cho phép gỡ lỗi USB trên điện thoại.
4. Mở ứng dụng trên PC, bấm Kiểm tra kết nối.
5. Chọn APK trên máy tính và bấm CÀI APK VÀO ĐIỆN THOẠI.
6. Tab Quản lý ứng dụng cho phép xem app người dùng và gỡ app đã chọn. Thao tác gỡ có thể xóa dữ liệu và luôn cần xác nhận.

## Nếu không nhận điện thoại
- Thử cáp/cổng USB khác; một số cáp chỉ có chức năng sạc.
- Mở khóa điện thoại và chấp nhận lời nhắc Gỡ lỗi USB.
- Trên Windows, một số điện thoại cần cài driver USB của hãng.
- Trạng thái unauthorized nghĩa là điện thoại chưa cấp quyền ADB.
- Công cụ không vượt khóa quản trị hoặc chính sách bảo mật Android.

## Tự build EXE
Cài Python 3.10 trở lên rồi chạy build_windows.bat. Batch sẽ tải Platform-Tools từ Google, cài PyInstaller và tạo dist\ADBEasyInstaller.exe.

Nguồn Android Platform-Tools chính thức:
https://developer.android.com/tools/releases/platform-tools

## Quyền riêng tư và an toàn
- Giao diện dùng Tkinter; không cần PyQt hay Android Studio.
- Không gửi nhật ký hoặc thông tin thiết bị lên mạng.
- Cài đặt dùng lệnh ADB thông thường và không tự gỡ bản cũ khi lỗi chữ ký.
- Gỡ ứng dụng chỉ chạy sau khi người dùng xác nhận.
