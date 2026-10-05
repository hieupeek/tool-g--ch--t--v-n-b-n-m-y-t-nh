# ⚡ AutoTyper Pro - Tool Tự Động Gõ Văn Bản Thông Minh

Ứng dụng mô phỏng gõ phím tự động vào bất kỳ ứng dụng nào: **Microsoft Word, Google Docs, Notepad, trình duyệt web**, và đặc biệt **hỗ trợ gõ trực tiếp qua màn hình điều khiển từ xa (Remote Desktop, AnyDesk, TeamViewer, UltraViewer)**.

---

## 🌟 Điểm nổi bật
- **Không cần cài đặt thư viện ngoài (Zero-dependency):** Sử dụng 100% thư viện chuẩn của Python, chạy được ngay trên cả Windows và macOS.
- **Hỗ trợ gõ tiếng Việt Unicode chuẩn:** Không lo bị lỗi dấu hay xung đột bộ gõ Unikey / EVKey.
- **Phím tắt toàn cục cực nhạy:** 
  - `Ctrl + Shift + Enter`: Tự động kích hoạt gõ ngay tại vị trí con trỏ chuột.
  - `Esc`: Dừng gõ khẩn cấp ngay lập tức.
- **Tiếp tục gõ từ vị trí dừng (Resume Typing):**
  - Khi bạn bấm dừng (hoặc ấn `Esc`), tool sẽ **ghi nhớ chính xác ký tự đang gõ dở**.
  - Phần văn bản đã gõ xong sẽ được làm mờ trên màn hình để bạn dễ theo dõi.
  - Bấm lại nút **▶ TIẾP TỤC GÕ (từ ký tự X)** hoặc ấn lại `Ctrl + Shift + Enter`, tool sẽ **gõ tiếp phần còn lại** mà không phải gõ lại từ đầu.
  - Có sẵn nút **`↻ Gõ lại từ đầu`** nếu bạn muốn bắt đầu lại từ ký tự đầu tiên.
- **Hỗ trợ điều khiển từ xa (Remote Desktop):**
  - Sử dụng cơ chế đọc trạng thái bàn phím tầng sâu (`GetAsyncKeyState`), vẫn bắt được phím tắt ngay cả khi đang focus vào cửa sổ Remote Desktop.
  - Có chế độ **Đếm ngược (3s - 5s)**: Bấm nút rồi thong thả click chuột sang màn hình remote để tool tự gõ.
- **Mô phỏng người thật gõ:** Tùy chọn tốc độ ngẫu nhiên ±15ms và nghỉ nhẹ ở các dấu câu `.` `,` `!` `?` `\n` giúp vượt qua các hệ thống kiểm tra/chống copy-paste.
- **Đóng gói thành file `.exe` tiện lợi:** Chỉ với 1 cú click chuột trên Windows.

---

## 🚀 Hướng Dẫn Sử Dụng Trên Windows

### Cách 1: Chạy trực tiếp qua Python
1. Đảm bảo máy đã cài [Python](https://www.python.org/) (nhớ tích chọn **"Add Python to PATH"** khi cài).
2. Nhấp đúp chuột vào file `run.bat` (hoặc chạy lệnh `python auto_typer.py`).

### Cách 2: Đóng gói thành file `.exe` độc lập (Khuyên dùng)
1. Nhấp đúp vào file `build_exe.bat`.
2. Chờ khoảng 15–30 giây, một thư mục tên `dist` sẽ xuất hiện chứa file:
   👉 **`dist\AutoTyper_Pro.exe`**
3. Bạn có thể mang file `.exe` này sang bất kỳ máy Windows nào để dùng mà **không cần cài Python**.

---

## 🍎 Hướng Dẫn Sử Dụng Trên macOS
1. Mở Terminal tại thư mục này.
2. Chạy lệnh:
   ```bash
   python3 auto_typer.py
   ```
   *(Hoặc nhấp đúp chạy `./run.sh`)*

---

## 🎯 Quy Trình Gõ Vào Remote Desktop (AnyDesk / TeamViewer / RDP)
1. Mở tool **AutoTyper Pro** lên.
2. Dán đoạn văn bản cần gõ vào khung.
3. Đặt tốc độ gõ khoảng **30ms – 50ms** (đây là tốc độ tối ưu để truyền dữ liệu qua mạng mà không bị nuốt chữ).
4. Bạn có 2 cách kích hoạt:
   - **Cách A (Dùng phím tắt):** Click chuột vào ô nhập liệu bên trong màn hình Remote Desktop -> Ấn tổ hợp phím **`Ctrl + Shift + Enter`**.
   - **Cách B (Dùng nút đếm ngược - Khuyên dùng):** Bấm nút **▶ BẮT ĐẦU GÕ (Đếm ngược 3s)** trên tool -> Click chuột sang màn hình Remote Desktop -> Hết 3 giây, tool sẽ tự động gõ toàn bộ văn bản vào.
5. Nếu muốn dừng giữa chừng: Ấn phím **`Esc`**.
