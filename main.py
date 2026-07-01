import os
import sys
<<<<<<< HEAD

# Xóa các biến môi trường SSL lỗi nếu có (do cài đặt PostgreSQL trên Windows tạo ra)
for ssl_env_var in ["REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE"]:
    if ssl_env_var in os.environ and "PostgreSQL" in os.environ[ssl_env_var]:
        del os.environ[ssl_env_var]

=======
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
import uuid
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
<<<<<<< HEAD
from fastapi import FastAPI, File, HTTPException, UploadFile, Request, BackgroundTasks, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
=======
from fastapi import FastAPI, File, HTTPException, UploadFile, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

<<<<<<< HEAD
import hmac
import hashlib
import json
import base64
import pymysql

SESSION_COOKIE_NAME = "kol_session"
SESSION_SECRET = os.getenv("SESSION_SECRET", "super_secret_session_key_12345").encode('utf-8')

def sign_session(data: dict) -> str:
    serialized = json.dumps(data).encode('utf-8')
    signature = hmac.new(SESSION_SECRET, serialized, hashlib.sha256).hexdigest()
    encoded_data = base64.urlsafe_b64encode(serialized).decode('utf-8')
    return f"{encoded_data}.{signature}"

def get_session(request: Request) -> dict | None:
    cookie_val = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie_val or "." not in cookie_val:
        return None
    try:
        encoded_data, signature = cookie_val.split(".", 1)
        serialized = base64.urlsafe_b64decode(encoded_data.encode('utf-8'))
        expected_signature = hmac.new(SESSION_SECRET, serialized, hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return json.loads(serialized.decode('utf-8'))
    except Exception as e:
        print(f"Session verification failed: {e}")
    return None

=======
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
# Reconfigure stdout/stderr to support UTF-8 Vietnamese characters on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Import the OCR processor from the existing ocr directory
from ocr.app.cccd_processor import process_cccd

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "ocr" / "data"
UPLOAD_TEMP_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/jpg": ".jpg"}

app = FastAPI(title="KOL Vendor System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "kolvendor"),
        cursorclass=pymysql.cursors.DictCursor
    )

=======
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
# Serves uploaded documents
app.mount("/uploads", StaticFiles(directory="public/uploads"), name="uploads")
# Serves frontend public assets
app.mount("/public", StaticFiles(directory="public"), name="public")

@app.get("/")
def index() -> FileResponse:
    return FileResponse("public/index.html")

@app.get("/dataBank.json")
def get_databank() -> FileResponse:
    return FileResponse("public/dataBank.json")

@app.get("/data_2025.json")
def get_data_2025() -> FileResponse:
    return FileResponse("public/data_2025.json")

# Header columns order requested by USER for the Google Sheet
HEADERS = [
    "Là tổ chức/cá nhân", "Là khách hàng", "Mã nhà cung cấp (*)", "Tên nhà cung cấp (*)", "Địa chỉ", "Mã số thuế", 
    "Điện thoại", "Fax", "Email", "Website", "Nhóm KH/NCC", "Số CCCD", "Ngày cấp", "Nơi cấp", "Xưng hô", 
    "Họ và tên NLH", "Chức danh", "Địa chỉ người liên hệ", "ĐT di động", "ĐT cơ quan", "ĐT di động khác", 
    "Email người liên hệ", "Số tài khoản", "Tên ngân hàng", "Chi nhánh", "Tỉnh/TP TK ngân hàng", "Tên tài khoản", 
    "Ngày tháng năm sinh", "STT", "Địa Chi Liên Lạc", "Link Profile", "Ảnh CCCD mặt trước", "Ảnh CCCD mặt sau", 
    "Ảnh Passport", "Giấy Phép Kinh Doanh", "Mã số thuế ( sửa đổi )", "Số CCCD ( sửa đổi )"
]

def get_sheets_service():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_credentials.json")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google credentials JSON file not found at: {creds_path}")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build("sheets", "v4", credentials=creds)
    return service

def get_drive_service():
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_credentials.json")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google credentials JSON file not found at: {creds_path}")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build("drive", "v3", credentials=creds)
    return service

def upload_to_drive(file_path: Path, filename: str, folder_id: str) -> str:
    try:
        service = get_drive_service()
        file_metadata = {
            "name": filename,
            "parents": [folder_id] if folder_id else []
        }
        suffix = file_path.suffix.lower()
        mimetype = "image/jpeg"
        if suffix == ".png":
            mimetype = "image/png"
        elif suffix == ".pdf":
            mimetype = "application/pdf"

        media = MediaFileUpload(str(file_path), mimetype=mimetype, resumable=True)
        file_obj = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()

        file_id = file_obj.get("id")

        try:
            service.permissions().create(
                fileId=file_id,
                body={
                    "role": "reader",
                    "type": "anyone"
                },
                supportsAllDrives=True
            ).execute()
        except Exception as pe:
            print(f"Error setting public permission for file {file_id}: {pe}")

        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    except Exception as e:
        print(f"Error uploading {filename} to Google Drive: {e}")
        return ""

def resolve_bank_bin(bank_code: str) -> str | None:
    try:
        r = requests.get('https://api.vietqr.io/v2/banks', timeout=10)
        if r.status_code == 200:
            res_data = r.json()
            if 'data' in res_data and isinstance(res_data['data'], list):
                for bank in res_data['data']:
                    if (bank.get('code', '').upper() == bank_code.upper() or 
                        bank.get('shortName', '').upper() == bank_code.upper() or 
                        bank.get('short_name', '').upper() == bank_code.upper()):
                        return bank.get('bin')
    except Exception as e:
        print(f"Error resolving bank bin: {e}")
    return None

@app.get("/check-bank-account")
async def check_bank_account(accountNumber: str, bankName: str):
    account_number = accountNumber.strip()
    bank_name = bankName.strip()

    if not account_number or not bank_name:
        return JSONResponse({"success": False, "message": "Vui lòng cung cấp số tài khoản và tên ngân hàng."})

    # Tách lấy mã ngân hàng
    parts = bank_name.split('-')
    bank_code = parts[0].strip()

    client_id = os.getenv("VIETQR_CLIENT_ID", "")
    api_key = os.getenv("VIETQR_API_KEY", "")

    if not client_id or not api_key:
        mock_name = 'NGUYEN VAN A'
        if len(account_number) % 2 == 0:
            mock_name = 'TRAN THI B'
        return JSONResponse({
            "success": True,
            "isDemo": True,
            "accountHolderName": mock_name,
            "message": "Thành công (Chế độ Demo - Hãy cấu hình VIETQR_CLIENT_ID và VIETQR_API_KEY trong file .env để chạy thực tế)"
        })

    bin_code = resolve_bank_bin(bank_code)
    if not bin_code:
        return JSONResponse({"success": False, "message": f"Không tìm thấy mã BIN của ngân hàng {bank_code}."})

    try:
        url = 'https://api.vietqr.io/v2/lookup'
        headers = {
            'Content-Type': 'application/json',
            'x-client-id': client_id,
            'x-api-key': api_key
        }
        payload = {
            'bin': bin_code,
            'accountNumber': account_number
        }
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            res_data = r.json()
            code = str(res_data.get('code', ''))
            if code == '00' and 'data' in res_data and res_data['data'] and 'accountName' in res_data['data']:
                return JSONResponse({
                    "success": True,
                    "accountHolderName": res_data['data']['accountName'].upper(),
                    "message": "Xác thực tài khoản thành công."
                })
            else:
                desc = res_data.get('desc', 'Thông tin tài khoản hoặc ngân hàng không khớp.')
                return JSONResponse({"success": False, "message": desc})
        else:
            return JSONResponse({"success": False, "message": f"VietQR API trả về mã lỗi {r.status_code}"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi hệ thống khi kết nối VietQR: {e}"})

async def save_upload(file: UploadFile, directory: Path, name: str) -> Path:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ ảnh JPG hoặc PNG.")

    suffix = ALLOWED_TYPES[file.content_type]
    path = directory / f"{name}{suffix}"

    size = 0
    with path.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                output.close()
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Mỗi ảnh không được vượt quá 5MB.")
            output.write(chunk)

    await file.seek(0)
    return path

@app.post("/api/read-cccd")
async def read_cccd(front: UploadFile | None = File(None), back: UploadFile | None = File(None)):
    UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    request_id = uuid.uuid4().hex
    upload_path = UPLOAD_TEMP_DIR / request_id
    upload_path.mkdir(parents=True, exist_ok=True)

    front_path = await save_upload(front, upload_path, "front") if front and front.filename else None
    back_path = await save_upload(back, upload_path, "back") if back and back.filename else None

    if not front_path and not back_path:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp ít nhất 1 ảnh mặt trước hoặc mặt sau.")

    try:
        return process_cccd(front_path, back_path, RESULT_DIR)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Không xử lý được ảnh: {exc}") from exc
    finally:
        # Xóa thư mục upload tạm thời chứa ảnh CCCD để bảo mật và tiết kiệm ổ đĩa
        if upload_path.exists():
            import shutil
            shutil.rmtree(upload_path, ignore_errors=True)

@app.post("/submit")
async def submit_form(request: Request):
    form_data = await request.form()

    # Nhận các thông tin từ form
    vendor_group = form_data.get("vendorGroup", "").strip()
    vendor_name = form_data.get("vendorName", "").strip().upper()
    tax_code = (form_data.get("taxCodeEdited", "").strip() or form_data.get("taxCode", "").strip())
    phone = form_data.get("phone", "").strip()
    email = form_data.get("email", "").strip()
    communication_address = form_data.get("communicationAddress", "").strip()
    salutation = form_data.get("salutation", "").strip()
    bank_account_number = form_data.get("bankAccountNumber", "").strip()
    bank_name = form_data.get("bankName", "").strip()
    account_holder_name = form_data.get("accountHolderName", "").strip().upper()

    # Validation cơ bản
    if not (vendor_group and vendor_name and phone and email and communication_address and salutation and bank_account_number and bank_name and account_holder_name):
        return JSONResponse({"success": False, "message": "Vui lòng nhập đầy đủ các trường bắt buộc."})

    is_foreign_individual = (vendor_group == "Cá Nhân - Quốc tịch nước ngoài")
    is_individual = (vendor_group == "Cá nhân" or is_foreign_individual)

    if is_individual:
        id_number = (form_data.get("idNumberEdited", "").strip() or form_data.get("idNumber", "").strip())
        if is_foreign_individual and not tax_code:
            tax_code = id_number

    if not tax_code:
        return JSONResponse({"success": False, "message": "Mã số thuế hoặc Số định danh không được để trống."})

    # Kết nối Google Sheets và kiểm tra trùng MST, tính STT tiếp theo
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return JSONResponse({"success": False, "message": "GOOGLE_SHEET_ID chưa được cấu hình trong môi trường (.env)"})

    sheet_id = sheet_id.strip()
    if "/d/" in sheet_id:
        sheet_id = sheet_id.split("/d/")[1].split("/")[0]
    elif "/" in sheet_id:
        sheet_id = sheet_id.split("/")[0]

    try:
        service = get_sheets_service()
        sheets = service.spreadsheets()
        sheet_range = "Sheet1!A:AI"
        
        try:
            result = sheets.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
        except Exception:
            sheet_range = "A:AI"
            result = sheets.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
            
        rows = result.get("values", [])
        
        # Nếu sheet hoàn toàn trống, thêm hàng tiêu đề (Headers)
        if not rows:
            sheets.values().append(
                spreadsheetId=sheet_id,
                range=sheet_range,
                valueInputOption="RAW",
                body={"values": [HEADERS]}
            ).execute()
            rows = [HEADERS]
            
        # Kiểm tra trùng Mã số thuế (Mã số thuế ở cột thứ 6, index 5)
        tax_code_index = 5
        for row in rows[1:]:
            if len(row) > tax_code_index and row[tax_code_index] == tax_code:
                return JSONResponse({"success": False, "message": "Mã số thuế đã tồn tại trong hệ thống. Vui lòng kiểm tra lại."})
                
        # Lấy số thứ tự STT
        stt = len(rows)  # STT cho bản ghi tiếp theo (rows đã bao gồm tiêu đề)
        
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi kết nối hoặc truy vấn Google Sheets: {e}"})

    current_year = datetime.now().year
    vendor_code_base = f"KOL_{tax_code}"
    vendor_code_suffix = f"{current_year}_{stt}"
    vendor_code_full = f"{vendor_code_base}_{vendor_code_suffix}"

    # Xử lý upload file
    upload_dir = Path("public/uploads") / vendor_code_base
    upload_dir.mkdir(parents=True, exist_ok=True)

    drive_cccd_folder = os.getenv("GOOGLE_DRIVE_CCCD_FOLDER_ID", "").strip()
    drive_license_folder = os.getenv("GOOGLE_DRIVE_LICENSE_FOLDER_ID", "").strip()

    cccd_front_path = ""
    cccd_back_path = ""
    passport_path = ""
    business_license_path = ""

    async def save_vendor_file(file_field_name: str, suffix: str, is_license: bool = False) -> str:
        file = form_data.get(file_field_name)
        if not file or not file.filename:
            return ""
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".pdf"]:
            return ""

        new_filename = f"{vendor_code_full}_{suffix}{file_ext}"
        dest_path = upload_dir / new_filename

        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        
        # Upload to Google Drive
        folder_id = drive_license_folder if is_license else drive_cccd_folder
        drive_link = upload_to_drive(dest_path, new_filename, folder_id)
        if drive_link:
            return drive_link

        # Fallback to local server path if Google Drive upload failed
        return f"uploads/{vendor_code_base}/{new_filename}"

    if is_individual:
        if is_foreign_individual:
            passport_path = await save_vendor_file("passport", "Passport")
            if not passport_path:
                return JSONResponse({"success": False, "message": "Vui lòng tải lên Ảnh Passport hợp lệ."})
        else:
            cccd_front_path = await save_vendor_file("cccdFront", "CCCD_Front")
            cccd_back_path = await save_vendor_file("cccdBack", "CCCD_Back")
            if not cccd_front_path or not cccd_back_path:
                return JSONResponse({"success": False, "message": "Vui lòng tải lên đầy đủ Ảnh CCCD mặt trước và mặt sau."})
    else:
        business_license_path = await save_vendor_file("businessLicense", "GiayPhepKinhDoanh", is_license=True)
        if not business_license_path:
            return JSONResponse({"success": False, "message": "Vui lòng tải lên Ảnh Giấy phép kinh doanh hợp lệ."})

    # Lưu Google Sheets
    row_data = [
        'Cá nhân' if is_individual else 'Tổ chức',  # 1. Là tổ chức/cá nhân
        '',                                         # 2. Là khách hàng
        vendor_code_base,                           # 3. Mã nhà cung cấp (*)
        vendor_name,                                # 4. Tên nhà cung cấp (*)
        form_data.get("address", "").strip() if not is_foreign_individual else "",  # 5. Địa chỉ
        tax_code,                                   # 6. Mã số thuế
        phone,                                      # 7. Điện thoại
        '',                                         # 8. Fax
        email,                                      # 9. Email
        '',                                         # 10. Website
        vendor_group,                               # 11. Nhóm KH/NCC
        id_number if is_individual else "",        # 12. Số CCCD
        form_data.get("dateOfIssue", "").strip() if is_individual else "",        # 13. Ngày cấp
        (form_data.get("placeOfIssue", "").strip() or form_data.get("nationality", "").strip()) if is_individual else "",  # 14. Nơi cấp
        salutation,                                 # 15. Xưng hô
        form_data.get("contactFullName", "").strip() if not is_individual else "",  # 16. Họ và tên NLH
        form_data.get("jobTitle", "").strip() if not is_individual else "",        # 17. Chức danh
        form_data.get("contactAddress", "").strip() if not is_individual else "",  # 18. Địa chỉ người liên hệ
        form_data.get("mobilePhone", "").strip() if not is_individual else "",     # 19. ĐT di động
        vendor_code_suffix,                         # 20. ĐT cơ quan (lưu vendor_code_suffix giống schema cũ)
        form_data.get("secondaryMobilePhone", "").strip() if not is_individual else "", # 21. ĐT di động khác
        form_data.get("contactEmail", "").strip() if not is_individual else "",    # 22. Email người liên hệ
        bank_account_number,                        # 23. Số tài khoản
        bank_name,                                  # 24. Tên ngân hàng
        '',                                         # 25. Chi nhánh
        '',                                         # 26. Tỉnh/TP TK ngân hàng
        account_holder_name,                        # 27. Tên tài khoản
        form_data.get("dateOfBirth", "").strip() if is_individual else "",         # 28. Ngày tháng năm sinh
        stt,                                        # 29. STT
        communication_address,                      # 30. Địa Chi Liên Lạc
        form_data.get("linkProfile", "").strip(),  # 31. Link Profile
        cccd_front_path,                            # 32. Ảnh CCCD mặt trước
        cccd_back_path,                             # 33. Ảnh CCCD mặt sau
        passport_path,                              # 34. Ảnh Passport
        business_license_path,                      # 35. Giấy Phép Kinh Doanh
        form_data.get("taxCodeEdited", "").strip(),  # 36. Mã số thuế ( sửa đổi )
        form_data.get("idNumberEdited", "").strip()  # 37. Số CCCD ( sửa đổi )
    ]

    try:
        sheets.values().append(
            spreadsheetId=sheet_id,
            range=sheet_range,
            valueInputOption="RAW",
            body={"values": [row_data]}
        ).execute()
        return JSONResponse({
            "success": True,
            "message": "Đăng ký thành công!",
            "vendorCode": vendor_code_full
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi lưu thông tin vào Google Sheets: {e}"})

@app.post("/api/verify-sheets-mst")
<<<<<<< HEAD
async def verify_sheets_mst():
    import multiprocessing
    from verify_mst import run_sheets_verification
    
    # Chạy verify MST trong một Process riêng biệt thay vì Thread hoặc BackgroundTasks
    # Điều này giúp tránh bị lock GIL do thư viện ddddocr chiếm CPU-bound
    p = multiprocessing.Process(target=run_sheets_verification)
    p.start()
    
=======
async def verify_sheets_mst(background_tasks: BackgroundTasks):
    from verify_mst import run_sheets_verification
    background_tasks.add_task(run_sheets_verification)
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
    return JSONResponse({
        "success": True, 
        "message": "Tiến trình xác thực MST đã được kích hoạt chạy ngầm trên Google Sheets. Các dòng MST sẽ được tự động highlight màu sắc dựa trên kết quả xác thực."
    })

# Auto-verify scheduler: Runs every 12 hours
async def schedule_verification():
    import asyncio
<<<<<<< HEAD
    import multiprocessing
=======
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
    # Wait 60 seconds on startup before running the first check to let the app fully initialize
    await asyncio.sleep(60)
    while True:
        try:
            print("Starting scheduled 12-hour MST verification...")
            from verify_mst import run_sheets_verification
<<<<<<< HEAD
            
            # Khởi chạy trong Process riêng biệt để không chặn event loop
            p = multiprocessing.Process(target=run_sheets_verification)
            p.start()
            
            # Chờ Process chạy xong mà không block async loop
            while p.is_alive():
                await asyncio.sleep(5)
                
=======
            # We run it in a separate thread so it doesn't block the async event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, run_sheets_verification)
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
            print("Scheduled 12-hour MST verification finished.")
        except Exception as e:
            print(f"Error in scheduled MST verification: {e}")
        # Sleep for 12 hours (12 * 60 * 60 seconds)
        await asyncio.sleep(12 * 60 * 60)

<<<<<<< HEAD
# Helper functions for Local JSON Storage of Invitations
INVITATIONS_FILE = BASE_DIR / "invitations.json"

def read_invitations() -> list:
    if not INVITATIONS_FILE.exists():
        # Tạo file mặc định nếu chưa tồn tại
        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        default_data = []
        if admin_email:
            default_data.append({
                "id": 1,
                "email": admin_email,
                "invited_by": "system",
                "invited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "role": "admin"
            })
        with INVITATIONS_FILE.open("w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    try:
        with INVITATIONS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading invitations.json: {e}")
        return []

def write_invitations(data: list) -> bool:
    try:
        with INVITATIONS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error writing invitations.json: {e}")
        return False

def is_email_authorized(email: str) -> bool:
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if not email:
        return False
    if email.lower() == admin_email:
        return True
    
    invitations = read_invitations()
    for inv in invitations:
        if inv.get("email", "").lower() == email.lower():
            return True
    return False

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_invitation_email(recipient_email: str, invited_by: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass]):
        print("SMTP configurations missing in .env. Skipping email sending.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = "[KOL VENDOR PORTAL] Lời mời tham gia hệ thống tra cứu"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #3b82f6; margin-top: 0;">KOL VENDOR PORTAL</h2>
                <p>Xin chào,</p>
                <p>Bạn đã được quản trị viên <strong>{invited_by}</strong> mời tham gia hệ thống Tra cứu thông tin Nhà cung cấp.</p>
                <p>Vui lòng đăng nhập vào hệ thống bằng tài khoản Google của bạn theo đường dẫn dưới đây:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="http://127.0.0.1:8000/public/login.html" 
                       style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                       Đăng Nhập Ngay
                    </a>
                </p>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
                <p style="font-size: 0.85em; color: #718096;">Đây là email tự động từ hệ thống KOL VENDOR. Vui lòng không trả lời email này.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        port = int(smtp_port)
        # Zoho cổng 465 yêu cầu kết nối SMTP_SSL ngay từ đầu
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_host, port)
        else:
            server = smtplib.SMTP(smtp_host, port)
            server.starttls()
            
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipient_email, msg.as_string())
        server.quit()
        print(f"Sent invitation email to {recipient_email}")
        return True
    except Exception as e:
        print(f"Error sending invitation email: {e}")
        return False

@app.get("/api/auth/login")
def auth_login(request: Request, response: Response):
    # Google OAuth2 Login Redirect
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=400, 
            detail="Google OAuth chưa được cấu hình trên Server. Vui lòng sử dụng tính năng Đăng nhập thử nghiệm."
        )

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&state=kol_state"
    )
    return RedirectResponse(url=google_auth_url)

@app.get("/api/auth/callback")
def auth_callback(request: Request, code: str = None, error: str = None):
    if error:
        return RedirectResponse(url=f"/public/login.html?error={error}")
    if not code:
        return RedirectResponse(url="/public/login.html?error=Authorization+code+missing")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    try:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        res = requests.post(token_url, data=data, timeout=10)
        if res.status_code != 200:
            return RedirectResponse(url="/public/login.html?error=Failed+to+exchange+token")

        tokens = res.json()
        access_token = tokens.get("access_token")
        
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_res = requests.get(userinfo_url, headers=headers, timeout=10)
        if userinfo_res.status_code != 200:
            return RedirectResponse(url="/public/login.html?error=Failed+to+fetch+user+info")

        user_data = userinfo_res.json()
        email = user_data.get("email", "").strip().lower()
        if not email:
            return RedirectResponse(url="/public/login.html?error=Google+account+has+no+email")

        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        if is_email_authorized(email):
            # Lấy role từ file JSON
            user_role = "user"
            if email == admin_email:
                user_role = "admin"
            else:
                invitations = read_invitations()
                for inv in invitations:
                    if inv.get("email", "").lower() == email:
                        user_role = inv.get("role", "user")
                        break

            session_data = {
                "email": email,
                "role": user_role
            }
            signed_cookie = sign_session(session_data)
            res = RedirectResponse(url="/public/search.html")
            res.set_cookie(SESSION_COOKIE_NAME, signed_cookie, max_age=86400 * 7, httponly=True)
            return res
        else:
            import urllib.parse
            err_msg = urllib.parse.quote_plus("Email này chưa được mời tham gia hệ thống. Vui lòng liên hệ Admin.")
            return RedirectResponse(url=f"/public/login.html?error={err_msg}")

    except Exception as e:
        import urllib.parse
        err_msg = urllib.parse.quote_plus(f"Lỗi xác thực: {e}")
        return RedirectResponse(url=f"/public/login.html?error={err_msg}")

@app.get("/api/auth/logout")
def auth_logout(request: Request):
    res = RedirectResponse(url="/public/login.html")
    res.delete_cookie(SESSION_COOKIE_NAME)
    return res

@app.get("/api/auth/me")
def auth_me(request: Request):
    user = get_session(request)
    if user:
        return {"logged_in": True, "email": user.get("email"), "role": user.get("role")}
    return {"logged_in": False}

@app.post("/api/admin/invite")
def admin_invite(request: Request, payload: dict):
    user = get_session(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện thao tác này.")

    email_to_invite = payload.get("email", "").strip().lower()
    role_to_invite = payload.get("role", "user").strip().lower()
    if role_to_invite not in ["admin", "user"]:
        role_to_invite = "user"

    if not email_to_invite:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp email hợp lệ.")

    try:
        invitations = read_invitations()
        for inv in invitations:
            if inv.get("email", "").lower() == email_to_invite:
                raise HTTPException(status_code=400, detail="Email này đã được mời trước đó.")

        new_id = max([inv.get("id", 0) for inv in invitations]) + 1 if invitations else 1
        new_inv = {
            "id": new_id,
            "email": email_to_invite,
            "invited_by": user.get("email"),
            "invited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": role_to_invite
        }
        invitations.append(new_inv)
        write_invitations(invitations)

        send_invitation_email(email_to_invite, user.get("email"))
        return {"success": True, "message": f"Đã gửi lời mời tới {email_to_invite} với vai trò {role_to_invite}."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu trữ dữ liệu: {e}")

@app.get("/api/admin/invitations")
def admin_invitations(request: Request):
    user = get_session(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền truy cập Admin.")

    try:
        invitations = read_invitations()
        # Sắp xếp mới nhất lên đầu
        invitations.sort(key=lambda x: x.get("invited_at", ""), reverse=True)
        return {"success": True, "invitations": invitations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc dữ liệu: {e}")

@app.put("/api/admin/invite/{invitation_id}/role")
def admin_update_invite_role(request: Request, invitation_id: int, payload: dict):
    user = get_session(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện thao tác này.")

    new_role = payload.get("role", "").strip().lower()
    if new_role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Quyền hạn không hợp lệ.")

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()

    try:
        invitations = read_invitations()
        target_inv = None
        for inv in invitations:
            if inv.get("id") == invitation_id:
                target_inv = inv
                break

        if not target_inv:
            raise HTTPException(status_code=404, detail="Không tìm thấy lời mời này.")

        if target_inv.get("email", "").lower() == admin_email:
            raise HTTPException(status_code=400, detail="Không thể thay đổi quyền hạn của Admin tối cao.")

        target_inv["role"] = new_role
        write_invitations(invitations)
        return {"success": True, "message": f"Đã cập nhật quyền hạn thành công."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật dữ liệu: {e}")

@app.delete("/api/admin/invite/{invitation_id}")
def admin_delete_invite(request: Request, invitation_id: int):
    user = get_session(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện thao tác này.")

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()

    try:
        invitations = read_invitations()
        target_inv = None
        for inv in invitations:
            if inv.get("id") == invitation_id:
                target_inv = inv
                break

        if not target_inv:
            raise HTTPException(status_code=404, detail="Không tìm thấy lời mời này.")

        if target_inv.get("email", "").lower() == admin_email:
            raise HTTPException(status_code=400, detail="Không thể xóa Admin tối cao khỏi danh sách.")

        invitations = [inv for inv in invitations if inv.get("id") != invitation_id]
        write_invitations(invitations)
        return {"success": True, "message": f"Đã xóa thành viên khỏi danh sách được mời."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa dữ liệu: {e}")

@app.get("/search")
def search_page(request: Request) -> FileResponse:
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/public/login.html")
    return FileResponse("public/search.html")

@app.get("/api/search-vendor")
def search_vendor(request: Request, query: str = ""):
    user = get_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thực hiện tìm kiếm.")
    import re
    query = query.strip()
    if not query:
        return {"success": True, "results": []}

    try:
        service = get_sheets_service()
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise HTTPException(status_code=500, detail="GOOGLE_SHEET_ID not configured in .env")

        sheet_meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_meta.get("sheets", [])
        if not sheets:
            raise HTTPException(status_code=500, detail="No sheets found in spreadsheet.")

        target_sheet = sheets[0]
        for s in sheets:
            if s.get("properties", {}).get("title") == "Sheet1":
                target_sheet = s
                break
        tab_title = target_sheet.get("properties", {}).get("title", "Sheet1")

        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab_title}!A:AJ").execute()
        rows = result.get("values", [])

        if len(rows) <= 1:
            return {"success": True, "results": []}

        matched_results = []
        query_lower = query.lower()
        query_digits = re.sub(r"\D", "", query)

        for i in range(1, len(rows)):
            row = rows[i]
            # Pad row if it has fewer elements than HEADERS
            while len(row) < len(HEADERS):
                row.append("")

            # Extract fields safely
            vendor_group = row[0].strip()
            vendor_code = row[2].strip()
            vendor_name = row[3].strip()
            address = row[4].strip()
            mst = row[5].strip()
            phone = row[6].strip()
            email = row[8].strip()
            cccd = row[11].strip()
            date_of_issue = row[12].strip()
            place_of_issue = row[13].strip()
            salutation = row[14].strip()
            contact_name = row[15].strip()
            bank_acc = row[22].strip()
            bank_name = row[23].strip()
            bank_branch = row[24].strip()
            bank_holder = row[26].strip()
            dob = row[27].strip()
            comm_address = row[29].strip()
            mst_edited = row[35].strip()
            cccd_edited = row[36].strip()

            # Matching criteria
            match = False

            # 1. Match by Vendor Code
            if query_lower in vendor_code.lower():
                match = True
            # 2. Match by Vendor Name
            elif query_lower in vendor_name.lower():
                match = True
            # 3. Match by Contact Name
            elif query_lower in contact_name.lower():
                match = True
            # 4. Match by MST
            elif query_digits and (query_digits in re.sub(r"\D", "", mst) or query_digits in re.sub(r"\D", "", mst_edited)):
                match = True
            # 5. Match by CCCD
            elif query_digits and (query_digits in re.sub(r"\D", "", cccd) or query_digits in re.sub(r"\D", "", cccd_edited)):
                match = True

            if match:
                matched_results.append({
                    "vendor_group": vendor_group,
                    "vendor_code": vendor_code,
                    "vendor_name": vendor_name,
                    "address": address,
                    "mst": mst_edited if mst_edited else mst,
                    "phone": phone,
                    "email": email,
                    "cccd": cccd_edited if cccd_edited else cccd,
                    "date_of_issue": date_of_issue,
                    "place_of_issue": place_of_issue,
                    "salutation": salutation,
                    "contact_name": contact_name,
                    "bank_acc": bank_acc,
                    "bank_name": bank_name,
                    "bank_branch": bank_branch,
                    "bank_holder": bank_holder,
                    "dob": dob,
                    "comm_address": comm_address,
                    "all_fields": [{"label": header, "value": row[idx].strip()} for idx, header in enumerate(HEADERS)]
                })

        return {"success": True, "results": matched_results}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn dữ liệu từ Google Sheets: {e}")

=======
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(schedule_verification())
