import sys
from pathlib import Path
from ocr.app.cccd_processor import process_cccd

front_path = Path("ocr/data/uploads/f3241a1490864ec988d4dcca85250505/front.jpg")
back_path = Path("ocr/data/uploads/f3241a1490864ec988d4dcca85250505/back.jpg")
result_dir = Path("ocr/data/results")

try:
    print("Running process_cccd...")
    res = process_cccd(front_path, back_path, result_dir)
    print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
