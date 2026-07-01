# Web đọc thông tin CCCD

Ứng dụng local web gồm HTML/JS thuần và backend FastAPI. Ảnh CCCD được gửi lên server của bạn, lưu ảnh gốc để đối soát, đọc QR trước, sau đó dùng OCR để bổ sung field còn thiếu.

## Công nghệ

- Frontend: HTML, CSS, JavaScript thuần
- Backend: Python FastAPI
- QR: OpenCV QRCodeDetector
- OCR: EasyOCR tiếng Việt/Anh, chạy CPU
- Lưu kết quả: mỗi lượt đọc tạo một thư mục riêng trong `data/results`
- Lưu ảnh gốc: mỗi lượt upload tạo một thư mục riêng trong `data/uploads`

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Lần đầu chạy EasyOCR có thể tải model về máy. Model chạy local, không gửi ảnh CCCD đến dịch vụ bên thứ ba.

## Chạy web

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Mở trình duyệt tại:

```text
http://localhost:8000
```

Nếu muốn người khác truy cập tạm từ internet trên máy cá nhân, bạn cần mở port/router hoặc dùng tunnel như Cloudflare Tunnel/ngrok. Khi đó ảnh vẫn được xử lý trên máy đang chạy backend, nhưng đường truyền internet cần được bảo vệ vì dữ liệu CCCD là dữ liệu nhạy cảm.

## Field trả về

```json
{
  "so_cccd": "",
  "ho_va_ten": "",
  "ngay_sinh": "",
  "gioi_tinh": "",
  "quoc_tich": "Việt Nam",
  "que_quan": "",
  "noi_thuong_tru": "",
  "ngay_het_han": "",
  "ngay_cap": "",
  "noi_cap": ""
}
```

## Lưu ý triển khai

- Mỗi ảnh giới hạn 5MB.
- Mặt sau là optional.
- Nếu không đọc được QR, hệ thống vẫn trả kết quả OCR kèm cảnh báo.
- Không có đăng nhập trong bản này. Nếu public internet thật, nên thêm mật khẩu hoặc reverse proxy có Basic Auth trước khi dùng thực tế.
