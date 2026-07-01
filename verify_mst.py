import os
import sys
import time
import io
import html
import re
import requests
<<<<<<< HEAD
=======
import ddddocr
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

<<<<<<< HEAD
# Globals for lazy loading inside separate process
ocr_instance = None

def get_ocr():
    global ocr_instance
    if ocr_instance is None:
        import ddddocr
        ocr_instance = ddddocr.DdddOcr(show_ad=False)
    return ocr_instance
=======
# Initialize ddddocr
ocr = ddddocr.DdddOcr(show_ad=False)
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7

def get_sheets_service():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # Load env from root
    load_dotenv(override=True)
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_credentials.json")
    if not os.path.exists(creds_path):
        # Check relative to base dir
        base_dir = Path(__file__).resolve().parent
        creds_path = base_dir / creds_path
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Google credentials JSON file not found at: {creds_path}")
    creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    service = build("sheets", "v4", credentials=creds)
    return service

def solve_captcha_for_session(session, url_captcha):
    """Downloads the captcha image, processes transparency, and solves it using ddddocr."""
    try:
        captcha_url = f"{url_captcha}?uid={int(time.time() * 1000)}"
        r = session.get(captcha_url, verify=False, timeout=10)
        if r.status_code != 200:
            return None
        
        # Load image with PIL
        img = Image.open(io.BytesIO(r.content))
        
        # Paste onto white background to handle transparency
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.paste(img, (0, 0), img.convert("RGBA"))
            img_rgb = white_bg.convert("RGB")
        else:
            img_rgb = img.convert("RGB")
            
        img_byte_arr = io.BytesIO()
        img_rgb.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
<<<<<<< HEAD
        ocr = get_ocr()
=======
>>>>>>> 5fc33bb2ee5556146357b3512ae398e1ae1735f7
        captcha_text = ocr.classification(img_bytes)
        return captcha_text.strip()
    except Exception as e:
        print(f"Error solving captcha: {e}")
        return None

def query_gdt_portal(mst: str, is_individual: bool = True) -> str:
    """
    Queries the GDT portal for a given MST.
    Returns:
      "FOUND" if tax code exists.
      "NOT_FOUND" if tax code does not exist.
      "FAILED" if captcha solving fails after 10 retries.
    """
    url_main = "https://tracuunnt.gdt.gov.vn/tcnnt/mstcn.jsp" if is_individual else "https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp"
    url_captcha = "https://tracuunnt.gdt.gov.vn/tcnnt/captcha.png"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": url_main,
    }
    
    session = requests.Session()
    
    for attempt in range(10):
        try:
            print(f"[{mst}] Attempt {attempt + 1}/10...")
            # Init session
            session.get(url_main, headers=headers, verify=False, timeout=10)
            
            # Solve captcha
            captcha_text = solve_captcha_for_session(session, url_captcha)
            if not captcha_text:
                print(f"[{mst}] Solve captcha returned empty. Retrying...")
                continue
                
            payload = {
                "cm": "cm",
                "mst": mst,
                "fullname": "",
                "address": "",
                "cmt": "",
                "captcha": captcha_text
            }
            
            r_post = session.post(url_main, data=payload, headers=headers, verify=False, timeout=10)
            html_content = html.unescape(r_post.text)
            
            if "mã xác nhận không đúng" in html_content.lower() or "nhập đúng mã xác nhận" in html_content.lower() or "vui lòng nhập mã xác nhận" in html_content.lower():
                print(f"[{mst}] Incorrect captcha. Retrying...")
                continue
            
            # Parse result
            if "không tìm thấy người nộp thuế nào phù hợp" in html_content.lower() or "không thấy kết quả" in html_content.lower() or "không hợp lệ" in html_content.lower():
                return "NOT_FOUND"
            elif "bảng thông tin tra cứu" in html_content.lower():
                return "FOUND"
            else:
                # Unexpected response, could be temp error, try again
                snippet = html_content[:300].replace('\n', ' ')
                print(f"[{mst}] Unexpected response (snippet: {snippet}). Retrying...")
                continue
                
        except Exception as e:
            print(f"[{mst}] Exception during query: {e}")
            time.sleep(1)
            
    return "FAILED"

def verify_single_mst(mst: str, is_individual: bool = True) -> str:
    """
    Verifies MST. First tries preferred portal. If not found and group is mixed,
    tries the other portal.
    """
    mst = re.sub(r'\D', '', mst) # Keep only digits
    if not mst:
        return "NOT_FOUND"
        
    result = query_gdt_portal(mst, is_individual=is_individual)
    
    # Fallback to the other portal if not found, to handle mixed category registers
    if result == "NOT_FOUND":
        print(f"[{mst}] Not found in preferred portal. Trying fallback portal...")
        result = query_gdt_portal(mst, is_individual=not is_individual)
        
    return result

def update_cell_color(service, sheet_id, spreadsheet_tab_id, row_idx, col_idx, status):
    """
    Updates Google Sheet cell background color using batchUpdate.
    Green (#b6d7a8): FOUND
    Red (#ff9999): NOT_FOUND
    Yellow (#ffe599): FAILED
    """
    colors = {
        "FOUND": {"red": 182/255.0, "green": 215/255.0, "blue": 168/255.0},      # Light Green
        "NOT_FOUND": {"red": 255/255.0, "green": 153/255.0, "blue": 153/255.0},  # Light Red
        "FAILED": {"red": 255/255.0, "green": 229/255.0, "blue": 153/255.0}       # Light Yellow
    }
    
    color = colors.get(status)
    if not color:
        return
        
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": spreadsheet_tab_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }
    
    try:
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        print(f"Successfully formatted cell row {row_idx + 1}, col {col_idx + 1} to {status}")
    except Exception as e:
        print(f"Error formatting cell: {e}")

def run_sheets_verification():
    load_dotenv()
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("GOOGLE_SHEET_ID not configured in .env")
        return
        
    sheet_id = sheet_id.strip()
    if "/d/" in sheet_id:
        sheet_id = sheet_id.split("/d/")[1].split("/")[0]
    elif "/" in sheet_id:
        sheet_id = sheet_id.split("/")[0]

    try:
        service = get_sheets_service()
    except Exception as e:
        print(f"Failed to initialize Google Sheets service: {e}")
        return

    # Fetch spreadsheet sheets to find tab ID
    try:
        sheet_meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_meta.get("sheets", [])
        if not sheets:
            print("No sheets found in spreadsheet.")
            return
        
        # Let's find "Sheet1" or the first tab
        target_sheet = sheets[0]
        # We can look for Sheet1
        for s in sheets:
            if s.get("properties", {}).get("title") == "Sheet1":
                target_sheet = s
                break
                
        tab_id = target_sheet.get("properties", {}).get("sheetId", 0)
        tab_title = target_sheet.get("properties", {}).get("title", "Sheet1")
        print(f"Using sheet tab: {tab_title} (ID: {tab_id})")
        
        # Read rows
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab_title}!A:AJ").execute()
        rows = result.get("values", [])
        
        if len(rows) <= 1:
            print("No records to verify (only headers or empty sheet).")
            return
            
        print(f"Found {len(rows) - 1} records to verify.")
        
        # We will iterate through data rows starting from index 1 (second row)
        for i in range(1, len(rows)):
            row = rows[i]
            
            # Identify columns
            # Column 1 (index 0): "Là tổ chức/cá nhân" (e.g. Cá nhân/Tổ chức)
            # Column 6 (index 5): "Mã số thuế" (original)
            # Column 36 (index 35): "Mã số thuế ( sửa đổi )"
            
            is_individual = True
            if len(row) > 0:
                is_individual = (row[0].strip().lower() != "tổ chức")
                
            # Get MST
            mst = ""
            mst_col_idx = 5 # Original MST column (F)
            
            # First check if modified MST exists
            if len(row) > 35 and row[35].strip():
                mst = row[35].strip()
                mst_col_idx = 35 # Use modified column index for highlight
            elif len(row) > 5 and row[5].strip():
                mst = row[5].strip()
                mst_col_idx = 5
                
            if not mst:
                print(f"Row {i + 1}: No MST found, skipping.")
                continue
                
            print(f"\n--- Row {i + 1}: Verifying MST {mst} (Individual={is_individual}) ---")
            
            # Verify MST
            status = verify_single_mst(mst, is_individual=is_individual)
            print(f"Row {i + 1} Result: {status}")
            
            # Update background color in Sheets
            update_cell_color(service, sheet_id, tab_id, i, mst_col_idx, status)
            
            # Sleep slightly to avoid rate limiting
            time.sleep(2)
            
    except Exception as e:
        print(f"Error running sheets verification: {e}")

if __name__ == "__main__":
    run_sheets_verification()
