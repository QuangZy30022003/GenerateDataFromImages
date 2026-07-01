# Hướng dẫn sử dụng chi tiết: Công cụ Đăng ký Nhà cung cấp (Vendor Registration Tool)

Tài liệu này hướng dẫn chi tiết cách cài đặt, cấu hình và sử dụng hệ thống đăng ký nhà cung cấp tự động dựa trên Google Sheets và Google Drive.

---

## 1. Giới thiệu tổng quan
Hệ thống bao gồm:
- **Giao diện đăng ký (HTML/JS)**: Biểu mẫu hiện đại giúp nhà cung cấp nhập liệu trực quan, có tính năng tự động gợi ý tên ngân hàng và tải lên hình ảnh pháp lý.
- **Xử lý phía Backend (Google Apps Script)**: Tự động tiếp nhận dữ liệu từ biểu mẫu, xử lý định dạng, lưu trữ hồ sơ liên quan vào Google Drive và ghi nhận thông tin vào Google Sheets.

---

## 2. Hướng dẫn thiết lập (Dành cho Quản trị viên)

### Bước 1: Tạo Google Sheets
1. Truy cập [Google Sheets](https://docs.google.com/spreadsheets).
2. Tạo một file mới hoặc sử dụng file hiện có. Ghi lại **ID của Spreadsheet** (là chuỗi ký tự nằm trong URL, ví dụ: `1Pn2dhgFSb...`).
3. Đặt tên một tab (sheet) là `NCC` (hoặc tùy chỉnh trong code).

### Bước 2: Tạo Thư mục Google Drive (Lưu ảnh)
1. Tạo 2 thư mục trên Google Drive để lưu:
   - **Ảnh CCCD/Passport**: Ghi lại ID thư mục này.
   - **Ảnh Giấy phép kinh doanh**: Ghi lại ID thư mục này.
2. Đảm bảo tài khoản chạy Google Apps Script có quyền ghi vào các thư mục này.

### Bước 3: Cài đặt Google Apps Script (`appscript.js`)
1. Trong Google Sheet, chọn **Extensions** > **Apps Script**.
2. Sao chép nội dung file `appscript.js` vào trình soạn thảo.
3. Thay thế các thông tin cấu hình ở đầu file:
   - `SPREADSHEET_ID`: ID của Google Sheet.
   - `TARGET_FOLDER_ID`: ID thư mục lưu ảnh CCCD/Passport.
   - `BUSINESS_LICENSE_FOLDER_ID`: ID thư mục lưu ảnh GPKD.
4. Chọn **Deploy** > **New Deployment**:
   - **Type**: Web app
   - **Execute as**: Me
   - **Who has access**: Anyone
5. Sau khi Deploy thành công, sao chép **Web App URL**.

### Bước 4: Cấu hình Giao diện (`index.html`)
1. Mở file `index.html`.
2. Tìm dòng `const SCRIPT_URL = '...';` (khoảng dòng 619).
3. Paste **Web App URL** vừa nhận được ở Bước 3 vào đây.

### Bước 5: Khởi chạy dự án local (FastAPI)
Dự án đã được chuyển đổi hoàn toàn sang Python (FastAPI). Chỉ cần chạy một máy chủ duy nhất:

1. **Cấu hình môi trường và Cài đặt thư viện:**
   - Đảm bảo MySQL đã được bật (ví dụ qua XAMPP).
   - Di chuyển vào thư mục dự án và kích hoạt môi trường ảo:
     ```bash
     ocr\.venv\Scripts\activate
     ```
   - Cài đặt các thư viện cần thiết từ file `requirements.txt` ở root (nếu chưa cài):
     ```bash
     pip install -r requirements.txt
     ```

2. **Khởi chạy Máy chủ FastAPI:**
   - Chạy lệnh sau từ thư mục gốc của dự án:
     ```bash
     uvicorn main:app --port 8000 --reload
     ```
   - Truy cập giao diện tại: `http://localhost:8000`

---

## 3. Hướng dẫn sử dụng phía Người dùng

### Nhập liệu thông tin
- **Nhóm KH/NCC**: Bắt buộc chọn một trong ba nhóm: *Cá nhân*, *Công ty*, hoặc *Hộ kinh doanh*. Tùy vào lựa chọn này mà các trường thông tin tiếp theo sẽ hiển thị phù hợp.
- **Tên nhà cung cấp**: Hệ thống tự động chuyển sang chữ **IN HOA**.
- **Địa chỉ/Địa chỉ liên lạc**: Hệ thống tự động chuyển sang định dạng **Viết Hoa Chữ Đầu**.
- **Mã số thuế**: Là trường thông tin duy nhất để xác định nhà cung cấp. Hệ thống sẽ báo lỗi nếu mã số thuế đã tồn tại trong danh sách.
- **Tên ngân hàng**: Chỉ cần gõ tên hoặc mã ngân hàng, hệ thống sẽ hiển thị gợi ý để chọn.

### Tải lên hình ảnh
- Đối với **Cá nhân**: Cần tải lên ảnh mặt trước + mặt sau CCCD HOẶC ảnh Passport.
- Đối với **Công ty/Hộ kinh doanh**: Cần tải lên ảnh Giấy phép kinh doanh.
- *Lưu ý*: Chỉ chấp nhận các định dạng ảnh phổ biến (JPG, PNG, v.v.).

### Xác nhận gửi form
1. Sau khi điền đầy đủ thông tin, nhấn **Gửi đăng ký**.
2. Hệ thống sẽ kiểm tra tính hợp lệ (độ tuổi, định dạng email, v.v.).
3. Khi thành công, một thông báo sẽ hiện ra kèm theo **Mã nhà cung cấp** (Ví dụ: `KOL_MST_2026_01`).

---

## 4. Quản lý dữ liệu sau khi đăng ký

### Trên Google Sheets
- Dữ liệu sẽ tự động được ghi vào sheet `NCC`.
- Một bản ghi log (thời gian, tên, MST) sẽ được lưu tại sheet `Logs`.
- Cột **Mã nhà cung cấp** được tạo tự động để quản lý hồ sơ.

### Trên Google Drive
- Mỗi nhà cung cấp sẽ có một thư mục riêng (đặt tên theo Mã nhà cung cấp).
- Hình ảnh được lưu với tên tệp đã được chuẩn hóa giúp dễ dàng tra cứu.

---

## 5. Các lưu ý quan trọng
- **Độ tuổi**: Người đăng ký nhóm **Cá nhân** phải từ 18 tuổi trở lên (tính dựa trên Ngày sinh).
- **Tính duy nhất**: Mã số thuế phải là duy nhất. Không thể đăng ký lại nếu MST đã tồn tại.
- **Hỗ trợ**: Nếu nhấn "Gửi" mà không thấy phản hồi, vui lòng kiểm tra kết nối mạng hoặc liên hệ quản trị viên để kiểm tra hạn ngạch (quota) của Google Apps Script.
