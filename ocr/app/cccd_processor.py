from __future__ import annotations

import csv
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False


FIELDS = [
    "so_cccd",
    "ho_va_ten",
    "ngay_sinh",
    "gioi_tinh",
    "quoc_tich",
    "que_quan",
    "noi_thuong_tru",
    "noi_cu_tru",
    "noi_dang_ky_khai_sinh",
    "ngay_het_han",
    "ngay_cap",
    "noi_cap",
]

DATE_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})")
ID_RE = re.compile(r"\b\d{12}\b")

NAME_CORRECTION = {
    "ĐÔ": "ĐỖ",
    "ĐO": "ĐỖ",
    "Đ0": "ĐỖ",
    "VU": "VŨ",
    "VO": "VÕ",
    "VUONG": "VƯƠNG",
    "VUƠNG": "VƯƠNG",
    "QUANQ": "QUANG",
    "NGUYEN": "NGUYỄN",
    "NGUYÊN": "NGUYỄN",
    "LE": "LÊ",
    "HOANG": "HOÀNG",
    "TRAN": "TRẦN",
    "TRÂN": "TRẦN",
    "PHAM": "PHẠM",
    "PHÁM": "PHẠM",
    "BUI": "BÙI",
    "DANG": "ĐẶNG",
    "ĐANG": "ĐẶNG",
    "NGO": "NGÔ",
    "HUYNH": "HUỲNH",
    "TRINH": "TRỊNH",
    "LUONG": "LƯƠNG",
    "PHUNG": "PHÙNG",
    "QUACH": "QUÁCH",
    "LY": "LÝ",
    "LAM": "LÂM",
    "DIEP": "DIỆP",
    "HA": "HÀ",
    "TA": "TẠ",
    "CAO": "CAO",
}

ADDRESS_CORRECTION = {
    "Binh": "Bình",
    "binh": "bình",
    "Phưởc": "Phước",
    "phưởc": "phước",
    "Quãng": "Quảng",
    "quãng": "quảng",
    "Ngai": "Ngãi",
    "ngai": "ngãi",
    "Tỉnh": "Tỉnh",
    "tỉnh": "tỉnh",
    "Thành": "Thành",
    "thành": "thành",
    "Phố": "Phố",
    "phố": "phố",
    "Quận": "Quận",
    "quận": "quận",
    "Huyện": "Huyện",
    "huyện": "huyện",
    "Thị": "Thị",
    "thị": "thị",
    "Xã": "Xã",
    "xã": "xã",
    "Phường": "Phường",
    "phường": "phường",
    "Đường": "Đường",
    "đường": "đường",
    "Việt": "Việt",
    "việt": "việt",
    "Nam": "Nam",
    "nam": "nam",
    "Viet": "Việt",
    "viet": "việt",
}

def correct_spelling(text: str, correction_dict: dict[str, str]) -> str:
    if not text:
        return ""
    words = re.split(r'(\s+|[,;./\-\(\)])', text)
    result = []
    for word in words:
        if word in correction_dict:
            result.append(correction_dict[word])
        elif word.upper() in correction_dict:
            corrected = correction_dict[word.upper()]
            if word.istitle():
                corrected = corrected.title()
            elif word.islower():
                corrected = corrected.lower()
            else:
                corrected = corrected.upper()
            result.append(corrected)
        else:
            result.append(word)
    return "".join(result)


_EASYOCR_INSTANCE = None
_PADDLE_OCR_INSTANCE = None


@dataclass
class OcrLine:
    text: str
    confidence: float
    box: list[list[float]]


def process_cccd(front_path: Path | None, back_path: Path | None, output_dir: Path) -> dict[str, Any]:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    result_dir = output_dir / run_id

    warnings: list[str] = []
    data = {field: "" for field in FIELDS}
    data["quoc_tich"] = "Việt Nam"

    front = load_image(front_path) if front_path else None
    back = load_image(back_path) if back_path else None

    if front is not None:
        front_quality = inspect_quality(front, "mặt trước")
        for q in front_quality:
            if "mờ" in q or "quá tối" in q:
                raise ValueError(f"{q} Vui lòng chụp lại ảnh rõ nét và sáng hơn.")
        warnings.extend(front_quality)
    if back is not None:
        back_quality = inspect_quality(back, "mặt sau")
        for q in back_quality:
            if "mờ" in q or "quá tối" in q:
                raise ValueError(f"{q} Vui lòng chụp lại ảnh rõ nét và sáng hơn.")
        warnings.extend(back_quality)

    qr_payloads = []
    for image, label in ((front, "mặt trước"), (back, "mặt sau")):
        if image is None:
            continue
        qr_text = read_qr_from_image(image)
        if qr_text:
            qr_payloads.append({"side": label, "raw": qr_text})

    qr_data: dict[str, str] = {}
    if qr_payloads:
        qr_data = parse_cccd_qr(qr_payloads[0]["raw"], side=qr_payloads[0]["side"])
        merge_missing(data, qr_data)
    else:
        warnings.append("Không đọc được QR, kết quả phụ thuộc vào OCR nên có thể cần đối soát ảnh gốc.")

    front_card = crop_card(front) if front is not None else None
    if front is not None and front_card is None:
        front_card = normalize_orientation(front)
    back_card = crop_card(back) if back is not None else None
    if back is not None and back_card is None:
        back_card = normalize_orientation(back)

    # 1. OCR Mặt trước (nếu thiếu trường bắt buộc, tự động xoay và thử lại)
    front_ocr = []
    if front_card is not None:
        front_ocr = run_ocr(front_card)
        front_data = parse_front_ocr(front_ocr)
        if not front_data.get("so_cccd") or not front_data.get("ho_va_ten"):
            for angle in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                rotated = cv2.rotate(front_card, angle)
                rotated_ocr = run_ocr(rotated)
                rotated_data = parse_front_ocr(rotated_ocr)
                if rotated_data.get("so_cccd") and rotated_data.get("ho_va_ten"):
                    front_card = rotated
                    front_ocr = rotated_ocr
                    break

    # 2. OCR Mặt sau (nếu thiếu nơi cấp, tự động xoay và thử lại)
    back_ocr = []
    if back_card is not None:
        back_ocr = run_ocr(back_card)
        back_data = parse_back_ocr(back_ocr)
        if not back_data.get("noi_cap"):
            for angle in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                rotated = cv2.rotate(back_card, angle)
                rotated_ocr = run_ocr(rotated)
                rotated_data = parse_back_ocr(rotated_ocr)
                if rotated_data.get("noi_cap"):
                    back_card = rotated
                    back_ocr = rotated_ocr
                    break

    ocr_data = parse_front_ocr(front_ocr)
    if back_ocr:
        merge_missing(ocr_data, parse_back_ocr(back_ocr))

    merge_ocr_data(data, ocr_data)

    # Apply spelling corrections
    data["ho_va_ten"] = correct_spelling(data["ho_va_ten"], NAME_CORRECTION)
    data["noi_thuong_tru"] = correct_spelling(data["noi_thuong_tru"], ADDRESS_CORRECTION)
    data["que_quan"] = correct_spelling(data["que_quan"], ADDRESS_CORRECTION)
    data["noi_cap"] = correct_spelling(data["noi_cap"], ADDRESS_CORRECTION)


    for required in ("so_cccd", "ho_va_ten", "ngay_sinh", "noi_thuong_tru"):
        if not data.get(required):
            warnings.append(f"Không trích xuất chắc chắn trường {required}.")

    if not data.get("ngay_cap") and back_path is None:
        warnings.append("Chưa upload mặt sau; ngày cấp chỉ có thể lấy nếu QR chứa dữ liệu này.")

    method_name = "Cách 2: Chụp ảnh -> Quét QR ngầm (từ ảnh chụp)" if qr_payloads else "Cách 3: Chụp ảnh -> Đọc dữ liệu OCR (từ ảnh chụp)"

    result = {
        "id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "method": method_name,
        "data": data,
        "warnings": warnings,
        "qr": qr_payloads,
        "ocr": {
            "front": [line.__dict__ for line in front_ocr],
            "back": [line.__dict__ for line in back_ocr],
        },
        "files": {
            "json": str(result_dir / "result.json"),
            "csv": str(result_dir / "result.csv"),
            "front_image": str(front_path) if front_path else "",
            "back_image": str(back_path) if back_path else "",
        },
    }

    # Print details to console logs
    print("=" * 50)
    print("THÔNG TIN QUÉT CCCD:")
    print(f"- Phương thức trích xuất: {method_name}")
    print(f"- Số CCCD: {data.get('so_cccd')}")
    print(f"- Họ và tên: {data.get('ho_va_ten')}")
    print(f"- Ngày sinh: {data.get('ngay_sinh')}")
    print(f"- Giới tính: {data.get('gioi_tinh')}")
    print(f"- Quốc tịch: {data.get('quoc_tich')}")
    print(f"- Quê quán: {data.get('que_quan')}")
    print(f"- Nơi thường trú: {data.get('noi_thuong_tru')}")
    print(f"- Nơi cư trú: {data.get('noi_cu_tru')}")
    print(f"- Nơi đăng ký khai sinh: {data.get('noi_dang_ky_khai_sinh')}")
    if data.get("ngay_cap"):
        print(f"- Ngày cấp: {data.get('ngay_cap')}")
    if data.get("noi_cap"):
        print(f"- Nơi cấp: {data.get('noi_cap')}")
    if warnings:
        print(f"- Cảnh báo: {', '.join(warnings)}")
    print("=" * 50)

    # save_result(result, result_dir)  # Disabled saving result files to disk
    return result


def load_image(path: Path | None) -> np.ndarray | None:
    if path is None:
        return None
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Không đọc được ảnh: {path}")
    return image


def inspect_quality(image: np.ndarray, label: str) -> list[str]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_light = float(gray.mean())
    warnings: list[str] = []
    if blur_score < 65:
        warnings.append(f"Ảnh {label} có dấu hiệu mờ, OCR có thể sai.")
    if mean_light < 45:
        warnings.append(f"Ảnh {label} quá tối.")
    if mean_light > 220:
        warnings.append(f"Ảnh {label} quá sáng hoặc bị lóa.")
    return warnings


def normalize_orientation(image: np.ndarray) -> np.ndarray:
    candidates = rotations(image)
    for candidate in candidates:
        if HAS_PYZBAR:
            decoded = pyzbar.decode(candidate)
            if decoded:
                return candidate
        else:
            qr_detector = cv2.QRCodeDetector()
            text, _, _ = qr_detector.detectAndDecode(candidate)
            if text:
                return candidate
    return image


def rotations(image: np.ndarray) -> list[np.ndarray]:
    return [
        image,
        cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
        cv2.rotate(image, cv2.ROTATE_180),
        cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
    ]


def check_qr_ratio(qr_w: float, qr_h: float, img_w: float, img_h: float):
    w_ratio = qr_w / img_w
    h_ratio = qr_h / img_h
    if w_ratio > 0.35 or h_ratio > 0.35:
        raise ValueError("Ảnh chụp quá cận cảnh mã QR, vui lòng chụp toàn bộ thẻ CCCD (không chụp mỗi góc mã QR).")


def read_qr_from_image(image: np.ndarray) -> str:
    # 1. Thử dùng PyZbar trước tiên (nếu có cài đặt) vì nó cực kỳ chính xác
    if HAS_PYZBAR:
        for candidate in rotations(image):
            # Quét trực tiếp ảnh gốc bằng pyzbar
            decoded_objs = pyzbar.decode(candidate)
            for obj in decoded_objs:
                text = obj.data.decode("utf-8", errors="ignore").strip()
                if text:
                    check_qr_ratio(obj.rect.width, obj.rect.height, candidate.shape[1], candidate.shape[0])
                    return text
            
            # Tiền xử lý: Cân bằng CLAHE
            gray = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            decoded_objs = pyzbar.decode(enhanced)
            for obj in decoded_objs:
                text = obj.data.decode("utf-8", errors="ignore").strip()
                if text:
                    check_qr_ratio(obj.rect.width, obj.rect.height, candidate.shape[1], candidate.shape[0])
                    return text

            # Nhị phân hóa thích ứng
            thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 12)
            decoded_objs = pyzbar.decode(thresh)
            for obj in decoded_objs:
                text = obj.data.decode("utf-8", errors="ignore").strip()
                if text:
                    check_qr_ratio(obj.rect.width, obj.rect.height, candidate.shape[1], candidate.shape[0])
                    return text

            # Co giãn ảnh đa quy mô
            for scale in [0.5, 0.75, 1.5, 2.0]:
                resized = cv2.resize(enhanced, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
                decoded_objs = pyzbar.decode(resized)
                for obj in decoded_objs:
                    text = obj.data.decode("utf-8", errors="ignore").strip()
                    if text:
                        # scale ratio back to candidates scale
                        check_qr_ratio(obj.rect.width / scale, obj.rect.height / scale, candidate.shape[1], candidate.shape[0])
                        return text

    # 2. Dự phòng bằng OpenCV QRCodeDetector mặc định (nếu pyzbar không khả dụng hoặc quét lỗi)
    detector = cv2.QRCodeDetector()
    for candidate in rotations(image):
        targets = [candidate]
        # Thử cả ảnh nắn thẳng (nếu crop được)
        card = crop_card(candidate)
        if card is not None:
            targets.append(card)

        for target in targets:
            # Quét trực tiếp
            text, points, _ = detector.detectAndDecode(target)
            if text:
                text = text.strip()
                if text and points is not None and len(points) > 0:
                    pts = points[0]
                    qr_w = max([p[0] for p in pts]) - min([p[0] for p in pts])
                    qr_h = max([p[1] for p in pts]) - min([p[1] for p in pts])
                    check_qr_ratio(qr_w, qr_h, target.shape[1], target.shape[0])
                return text
                
            # Xử lý xám + CLAHE
            gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            text, points, _ = detector.detectAndDecode(enhanced)
            if text:
                text = text.strip()
                if text and points is not None and len(points) > 0:
                    pts = points[0]
                    qr_w = max([p[0] for p in pts]) - min([p[0] for p in pts])
                    qr_h = max([p[1] for p in pts]) - min([p[1] for p in pts])
                    check_qr_ratio(qr_w, qr_h, target.shape[1], target.shape[0])
                return text
                
            # Nhị phân hóa
            thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 12)
            text, points, _ = detector.detectAndDecode(thresh)
            if text:
                text = text.strip()
                if text and points is not None and len(points) > 0:
                    pts = points[0]
                    qr_w = max([p[0] for p in pts]) - min([p[0] for p in pts])
                    qr_h = max([p[1] for p in pts]) - min([p[1] for p in pts])
                    check_qr_ratio(qr_w, qr_h, target.shape[1], target.shape[0])
                return text
                
            # Co giãn ảnh đa quy mô
            for scale in [0.5, 0.75, 1.3, 1.7]:
                resized = cv2.resize(target, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
                text, points, _ = detector.detectAndDecode(resized)
                if text:
                    text = text.strip()
                    if text and points is not None and len(points) > 0:
                        pts = points[0]
                        qr_w = (max([p[0] for p in pts]) - min([p[0] for p in pts])) / scale
                        qr_h = (max([p[1] for p in pts]) - min([p[1] for p in pts])) / scale
                        check_qr_ratio(qr_w, qr_h, target.shape[1], target.shape[0])
                    return text
    return ""


def crop_card(image: np.ndarray | None) -> np.ndarray | None:
    if image is None:
        return None
    oriented = normalize_orientation(image)
    ratio = 900 / max(oriented.shape[:2])
    resized = cv2.resize(oriented, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < resized.shape[0] * resized.shape[1] * 0.15:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.025 * peri, True)
        if len(approx) == 4:
            points = (approx.reshape(4, 2) / ratio).astype("float32")
            warped = warp_perspective(oriented, points)
            h, w = warped.shape[:2]
            if h > 0:
                aspect = w / h
                if 1.2 <= aspect <= 2.0:
                    return warped
    return None


def warp_perspective(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    rect = order_points(points)
    
    # Mở rộng các góc ra ngoài thêm 5% để tránh mất cạnh/cắt chữ ở mép thẻ
    center = np.mean(rect, axis=0)
    for i in range(4):
        dir_vec = rect[i] - center
        rect[i] = center + dir_vec * 1.05
        # Đảm bảo không vượt quá kích thước ảnh gốc
        rect[i][0] = np.clip(rect[i][0], 0, image.shape[1] - 1)
        rect[i][1] = np.clip(rect[i][1], 0, image.shape[0] - 1)
        
    width_a = np.linalg.norm(rect[2] - rect[3])
    width_b = np.linalg.norm(rect[1] - rect[0])
    height_a = np.linalg.norm(rect[1] - rect[2])
    height_b = np.linalg.norm(rect[0] - rect[3])
    max_width = int(max(width_a, width_b))
    max_height = int(max(height_a, height_b))
    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)
    rect[0] = points[np.argmin(sums)]
    rect[2] = points[np.argmax(sums)]
    rect[1] = points[np.argmin(diffs)]
    rect[3] = points[np.argmax(diffs)]
    return rect


def run_ocr(image: np.ndarray | None) -> list[OcrLine]:
    if image is None:
        return []
    try:
        return run_easyocr(image)
    except Exception:
        return run_paddle_ocr(image)


def run_easyocr(image: np.ndarray) -> list[OcrLine]:
    reader = get_easyocr()
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = reader.readtext(rgb, detail=1, paragraph=False)
    lines: list[OcrLine] = []
    for box, text, confidence in result:
        normalized = normalize_spaces(str(text))
        if normalized:
            lines.append(OcrLine(text=normalized, confidence=float(confidence), box=np.asarray(box).astype(float).tolist()))
    return sort_lines(lines)


def get_easyocr():
    global _EASYOCR_INSTANCE
    if _EASYOCR_INSTANCE is None:
        model_dir = Path(__file__).resolve().parent.parent / "data" / "easyocr_models"
        model_dir.mkdir(parents=True, exist_ok=True)
        import easyocr

        _EASYOCR_INSTANCE = easyocr.Reader(["vi", "en"], gpu=False, model_storage_directory=str(model_dir), verbose=False)
    return _EASYOCR_INSTANCE


def run_paddle_ocr(image: np.ndarray) -> list[OcrLine]:
    ocr = get_paddle_ocr()
    if hasattr(ocr, "predict"):
        result = ocr.predict(input=image)
    else:
        result = ocr.ocr(image, cls=True)
    parsed = parse_paddle3_result(result)
    if parsed:
        return sort_lines(parsed)

    lines: list[OcrLine] = []
    for page in result or []:
        for item in page or []:
            if len(item) < 2:
                continue
            box = [[float(v) for v in point] for point in item[0]]
            text = normalize_spaces(str(item[1][0]))
            confidence = float(item[1][1])
            if text:
                lines.append(OcrLine(text=text, confidence=confidence, box=box))
    return sort_lines(lines)


def get_paddle_ocr():
    global _PADDLE_OCR_INSTANCE
    if _PADDLE_OCR_INSTANCE is None:
        cache_dir = Path(__file__).resolve().parent.parent / "data" / "paddle_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_dir))
        os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        from paddleocr import PaddleOCR

        _PADDLE_OCR_INSTANCE = create_paddle_ocr(PaddleOCR)
    return _PADDLE_OCR_INSTANCE


def create_paddle_ocr(paddle_ocr_class):
    try:
        return paddle_ocr_class(
            lang="vi",
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
        )
    except ValueError:
        return paddle_ocr_class(use_angle_cls=True, lang="vi", use_gpu=False, show_log=False)


def parse_paddle3_result(result: Any) -> list[OcrLine]:
    lines: list[OcrLine] = []
    for page in result or []:
        page_json = getattr(page, "json", None)
        if isinstance(page_json, dict):
            payload = page_json.get("res", page_json)
        elif isinstance(page, dict):
            payload = page.get("res", page)
        else:
            continue

        texts = payload.get("rec_texts") or payload.get("texts") or []
        scores = payload.get("rec_scores") or payload.get("scores") or []
        boxes = payload.get("rec_polys") or payload.get("rec_boxes") or payload.get("dt_polys") or []
        for index, text in enumerate(texts):
            confidence = float(scores[index]) if index < len(scores) else 0.0
            raw_box = boxes[index] if index < len(boxes) else [[0, index * 20], [1, index * 20], [1, index * 20 + 1], [0, index * 20 + 1]]
            box = np.asarray(raw_box).reshape(-1, 2).astype(float).tolist()
            normalized = normalize_spaces(str(text))
            if normalized:
                lines.append(OcrLine(text=normalized, confidence=confidence, box=box))
    return lines


def sort_lines(lines: list[OcrLine]) -> list[OcrLine]:
    if not lines:
        return []
        
    # 1. Tính toán tọa độ y trung bình, x trung bình và chiều cao cho mỗi box
    line_data = []
    for line in lines:
        xs = [point[0] for point in line.box]
        ys = [point[1] for point in line.box]
        avg_y = sum(ys) / len(ys)
        avg_x = sum(xs) / len(xs)
        min_y = min(ys)
        max_y = max(ys)
        height = max_y - min_y
        line_data.append({
            "line": line,
            "avg_y": avg_y,
            "avg_x": avg_x,
            "min_y": min_y,
            "max_y": max_y,
            "height": height
        })
        
    # Sắp xếp các box theo y trung bình trước để nhóm từ trên xuống dưới
    line_data.sort(key=lambda item: item["avg_y"])
    
    grouped_rows = []
    for item in line_data:
        placed = False
        for row in grouped_rows:
            # Lấy phần tử đại diện của nhóm để so sánh
            rep = row[0]
            y_diff = abs(item["avg_y"] - rep["avg_y"])
            avg_height = (item["height"] + rep["height"]) / 2
            # Nếu chênh lệch y_center nhỏ hơn 60% chiều cao dòng trung bình, coi như cùng 1 dòng ngang
            if y_diff < avg_height * 0.6:
                row.append(item)
                placed = True
                break
        if not placed:
            grouped_rows.append([item])
            
    # 3. Với mỗi nhóm dòng ngang, sắp xếp các từ trái qua phải theo x
    sorted_lines = []
    for row in grouped_rows:
        row.sort(key=lambda item: item["avg_x"])
        # Ghép các text block trong dòng ngang lại với nhau bằng dấu cách
        combined_text = " ".join(item["line"].text for item in row)
        # Sử dụng box của phần tử đầu tiên làm đại diện
        rep_line = row[0]["line"]
        sorted_lines.append(OcrLine(text=combined_text, confidence=rep_line.confidence, box=rep_line.box))
        
    return sorted_lines


def parse_cccd_qr(raw: str, side: str = "mặt trước") -> dict[str, str]:
    parts = [normalize_spaces(part) for part in raw.strip().split("|")]
    data: dict[str, str] = {}
    if len(parts) >= 1 and re.fullmatch(r"\d{12}", parts[0]):
        data["so_cccd"] = parts[0]
    if len(parts) >= 3:
        data["ho_va_ten"] = title_case_name(parts[2])
    if len(parts) >= 4:
        data["ngay_sinh"] = normalize_date(parts[3])
    if len(parts) >= 5:
        data["gioi_tinh"] = normalize_gender(parts[4])
    if len(parts) >= 6:
        if side == "mặt sau":
            data["noi_cu_tru"] = parts[5]
        else:
            data["noi_thuong_tru"] = parts[5]
    if len(parts) >= 7:
        data["ngay_cap"] = normalize_date(parts[6])
    data["quoc_tich"] = "Việt Nam"
    return data


def split_glued_name(name: str) -> str:
    if not name:
        return ""
    words = name.split()
    fixed_words = []
    # Các tên chính và tên đệm thường gặp dễ bị dính chữ khi OCR
    common_first_names = [
        "VY", "ANH", "YEN", "TRANG", "LINH", "HUONG", "THAO", "HAI", "NAM", "MINH", 
        "QUAN", "KHANH", "DUNG", "PHUC", "TUNG", "DAT", "SON", "HUY", "HOANG", "PHONG", 
        "THU", "CHI", "NGA", "HOA", "MAI", "LAN", "CUC", "TRUC", "PHUONG", "BINH", "AN"
    ]
    for w in words:
        split_done = False
        # Nếu từ quá dài và kết thúc bằng một tên tiếng Việt phổ biến
        if len(w) >= 5:
            for fn in common_first_names:
                if w.endswith(fn) and len(w) > len(fn):
                    prefix = w[:-len(fn)]
                    # Chỉ cắt nếu phần trước cũng chứa nguyên âm hợp lệ (tránh cắt sai từ ngắn hoặc từ rác)
                    if any(v in prefix.upper() for v in ["A", "E", "I", "O", "U", "Y"]):
                        fixed_words.append(prefix)
                        fixed_words.append(fn)
                        split_done = True
                        break
        if not split_done:
            fixed_words.append(w)
    return " ".join(fixed_words)


def parse_front_ocr(lines: list[OcrLine]) -> dict[str, str]:
    texts = [line.text for line in lines]
    joined = "\n".join(texts)
    data: dict[str, str] = {}

    id_match = ID_RE.search(joined)
    if id_match:
        data["so_cccd"] = id_match.group(0)

    raw_name = after_label(texts, [
        "Họ và tên", "Ho va ten", "Full name", "Fullname", "Full nane", "Full nanve", "Ful name", "Hẹ vàten", "Ho ya ten", "Hoaten", "Hoten", "Họ yà tên",
        "Họ, chữ đệm và tên khai sinh", "Ho, chu dem va ten khai sinh", "Ho chu dem va ten khai sinh", "Họ, chữ đệm và tên", "Ho, chu dem va ten",
        "khai sinh", "chu dem", "full name", "fullname"
    ], join_uppercase_lines=True)
    if not raw_name:
        # Fallback to look for the uppercase name line
        raw_name = find_fallback_name(texts)
        
    if raw_name:
        data["ho_va_ten"] = split_glued_name(raw_name)

    data["ngay_sinh"] = find_date_near(texts, [
        "Ngày sinh", "Ngay sinh", "Date of birth", "Date of bith", "Date of brth", "Dateofbirth",
        "Ngày, tháng, năm sinh", "Ngay, thang, nam sinh", "nam sinh"
    ])
    data["gioi_tinh"] = find_gender(texts)
    data["quoc_tich"] = "Việt Nam"
    
    # Hỗ trợ cả mẫu mới (Nơi đăng ký khai sinh / Nơi cư trú) và mẫu cũ (Quê quán / Nơi thường trú)
    data["que_quan"] = clean_address(collect_between(texts, [
        "Quê quán", "Que quan", "Place of origin", "Place ofongln", "Place of origln", "Place of orlgin", "Placeoforigin", "Place of oigin",
        "Nơi đăng ký khai sinh", "Noi dang ky khai sinh", "Place of birth"
    ], [
        "Nơi thường trú", "Noi thuong tru", "Place of residence", "Placc cf fesidence", "Place of residenoe", "Place of residen",
        "Nơi cư trú", "Noi cu tru"
    ], max_lines=12))
    
    raw_address = collect_between(texts, [
        "Nơi thường trú", "Noi thuong tru", "Place of residence", "Placc cf fesidence", "Place of residenoe", "Place of residen",
        "Nơi cư trú", "Noi cu tru"
    ], [
        "Có giá trị", "Co gia tri", "Date of expiry", "Dateofexpiry", "Date of expir", "den ngay", "ngay het han", "co gia tri den", "gia tri den",
        "Nơi đăng ký khai sinh", "Noi dang ky khai sinh", "Place of birth"
    ], max_lines=12)
    data["noi_thuong_tru"] = clean_address(raw_address)
    
    data["ngay_het_han"] = find_date_near(texts, ["Có giá trị", "Co gia tri", "Date of expiry", "Dateofexpiry", "Date of expir", "đến", "den", "co gia tri den", "gia tri den"])
    return {key: value for key, value in data.items() if value}



def find_fallback_name(texts: list[str]) -> str:
    skip_words = [
        "CONG HOA", "XHCN", "VIET NAM", "DOC LAP", "TU DO", "HANH PHUC", 
        "CĂN CƯỚC", "CONG DAN", "CITIZEN", "IDENTITY", "CARD", "SO / NO", 
        "QUOC TICH", "QUE QUAN", "THUONG TRU", "GIA TRI", "EXPIRY", "BIRTH", 
        "ORIGIN", "RESIDENCE", "NAM", "NU", "SEX", "DATE", "SOCIALIST",
        "HO, CHU DEM VA TEN KHAI SINH", "HO CHU DEM VA TEN KHAI SINH", "KHAL SINH", "KHAI SINH", "FULL NAME"
    ]
    for text in texts:
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.isupper():
            comparable = strip_accents_for_match(stripped).upper()
            if any(strip_accents_for_match(word).upper() in comparable for word in skip_words):
                continue
            # Check if it has 2 to 6 words and only alphabetical characters
            cleaned = re.sub(r'[^a-zA-Z\sÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯẠẢẤẦẨẪẬẮẰClarẮẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲÝỶỸỴđĐ]', '', stripped)
            words = cleaned.split()
            if 2 <= len(words) <= 6:
                return stripped
    return ""


def clean_address(address_str: str) -> str:
    if not address_str:
        return ""
    
    # Loại bỏ các cụm từ tiếng Anh nhãn CCCD phổ biến
    english_patterns = [
        r'(?i)\bplace\s*of\s*residence\b',
        r'(?i)\bplace\s*of\s*origin\b',
        r'(?i)\bdate\s*of\s*birth\b',
        r'(?i)\bdate\s*of\s*expiry\b',
        r'(?i)\bfull\s*name\b',
        r'(?i)\bidentity\s*card\b',
        r'(?i)\bcitizen\s*identity\s*card\b',
        r'(?i)\bsocialist\s*republic\b'
    ]
    for pattern in english_patterns:
        address_str = re.sub(pattern, '', address_str)

    # Standardize string: replace multiple whitespaces/newlines with single space
    cleaned = re.sub(r'\s+', ' ', address_str).strip()
    
    # Split by comma, semicolon, or newlines
    parts = re.split(r'[,;\n]', cleaned)
    cleaned_parts = []
    
    junk_words = {
        "place", "of", "residence", "origin", "0rorpiny", "ororpiny", "placc", 
        "cf", "fesidence", "residenoe", "residen", "origi", "nơi", "thường", 
        "trú", "thuong", "tru", "dang", "ky", "dangky", "thuongtru", "diachi", 
        "dia", "chi", "address", "sex", "gender", "date", "birth", "expiry", "card", 
        "citizen", "fullname", "name", "no", "national", "nationality", "republic", 
        "socialist", "vietnam", "viet", "nam"
    }
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Check if this part contains mostly junk words or dates
        if DATE_RE.search(part):
            continue
            
        # Strip accents and compare lower case
        comparable = strip_accents_for_match(part).lower().strip(" :-/,.")
        
        # If the part is extremely short, skip it
        if len(comparable) < 2:
            continue
            
        # Check if the part is composed entirely of junk/noise words
        words = [w.strip(":-/,.") for w in comparable.split()]
        words = [w for w in words if w]
        
        # If all words in this part are junk, skip the part
        if words and all(w in junk_words for w in words):
            continue
            
        # Clean specific words inside the part (e.g. if part contains "0rorpiny" or "Place of residence")
        # Let's remove any words that are exact matches to junk words from this part
        cleaned_words = []
        for w in part.split():
            w_comp = strip_accents_for_match(w).lower().strip(":-/,.")
            if w_comp not in junk_words:
                cleaned_words.append(w)
        
        cleaned_part = " ".join(cleaned_words).strip(" :-/,.")
        if len(cleaned_part) >= 2:
            cleaned_parts.append(cleaned_part)
            
    final_address = ", ".join(cleaned_parts).strip()
    while True:
        prev_len = len(final_address)
        final_address = re.sub(r'(?i)\b(noi|thuong|tru|nơi|thường|trú|place|of|residence|residenoe|residen)\b\s*$', '', final_address).strip(" :-/,.")
        if len(final_address) == prev_len:
            break
            
    # Loại bỏ các phần trùng lặp từ phải qua trái để giữ đúng thứ tự hành chính Việt Nam (Xã, Huyện, Tỉnh)
    if final_address:
        addr_parts = [p.strip() for p in final_address.split(",") if p.strip()]
        seen = set()
        unique_parts = []
        for part in reversed(addr_parts):
            part_lower = strip_accents_for_match(part).lower()
            if part_lower not in seen:
                seen.add(part_lower)
                unique_parts.append(part)
        final_address = ", ".join(reversed(unique_parts))
        
    return final_address



def parse_back_ocr(lines: list[OcrLine]) -> dict[str, str]:
    texts = [line.text for line in lines]
    joined = "\n".join(texts)
    data: dict[str, str] = {}
    data["ngay_cap"] = find_date_near(texts, ["Ngày", "tháng", "năm", "Date", "month", "Yerr"], allow_global=True)
    
    # Nhận diện xem có phải mặt sau thẻ cũ hay không (thẻ cũ có Đặc điểm nhân dạng / Vân tay, không có địa chỉ ở mặt sau)
    is_old_card_back = False
    for t in texts:
        t_norm = strip_accents_for_match(t).lower()
        if any(w in t_norm for w in ["nhan dang", "nhan dag", "identi", "personal", "van tay", "ngon tro", "dac diem"]):
            is_old_card_back = True
            break
            
    if is_old_card_back:
        data["noi_cu_tru"] = ""
        data["noi_dang_ky_khai_sinh"] = ""
    else:
        # Hỗ trợ mẫu thẻ mới (Nơi cư trú và Nơi đăng ký khai sinh nằm ở mặt sau)
        data["noi_cu_tru"] = clean_address(collect_between(texts, ["Nơi cư trú", "Noi cu tru", "Place of residence"], ["Nơi đăng ký khai sinh", "Noi dang ky khai sinh", "Place of birth", "birth", "bith", "brth", "khai sinh", "Ngày", "tháng", "năm", "Date", "Ngay cap"], max_lines=12))
        data["noi_dang_ky_khai_sinh"] = clean_address(collect_between(texts, ["Nơi đăng ký khai sinh", "Noi dang ky khai sinh", "Place of birth"], ["Ngày", "tháng", "năm", "Date", "Ngay cap", "Bo Cong An", "Cuc Canh Sat"], max_lines=12))
    
    joined_upper = strip_accents_for_match(joined).upper()
    
    # Vì thẻ Căn cước mới không có nhãn "Nơi cấp:" mà chỉ in thẳng tên Cơ quan cấp,
    # chúng ta dùng cơ chế chấm điểm từ khoá để chọn Cơ quan cấp khớp nhất (Bộ Công An hoặc Cục Cảnh Sát)
    cuc_sat_score = 0
    cuc_sat_keywords = [
        "CUC", "CANH", "SAT", "QLHC", "TRAT", "TU", "XA", "HOI", "CUC CANH SAT", 
        "CVC", "S4T", "5AT", "TRATTV", "CUC TRUONG", "CVC TRUONG"
    ]
    for kw in cuc_sat_keywords:
        if kw in joined_upper:
            cuc_sat_score += 1
            
    bo_cong_an_score = 0
    bo_cong_an_keywords = [
        "BO", "CONG", "AN", "MINISTRY", "PUBLIC", "SECURITY", "BO CONG AN", 
        "CON6", "C0NG", "80", "B0", "CONG AN"
    ]
    for kw in bo_cong_an_keywords:
        if kw in joined_upper:
            bo_cong_an_score += 1
            
    if cuc_sat_score > 0 or bo_cong_an_score > 0:
        if bo_cong_an_score >= cuc_sat_score:
            data["noi_cap"] = "Bộ Công An"
        else:
            data["noi_cap"] = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
        
    return {key: value for key, value in data.items() if value}



def after_label(texts: list[str], labels: list[str], join_uppercase_lines: bool = False) -> str:
    for index, text in enumerate(texts):
        comparable = strip_accents_for_match(text).lower()
        for label in labels:
            label_key = strip_accents_for_match(label).lower()
            if label_key in comparable:
                value = remove_known_labels(text, labels).strip(" :-/")
                if value and not looks_like_label(value):
                    if join_uppercase_lines and value.isupper() and (index + 1 < len(texts)):
                        next_line = texts[index + 1].strip()
                        if next_line.isupper() and not looks_like_label(next_line):
                            value += " " + next_line
                    return normalize_spaces(value)
                
                for next_idx in range(index + 1, min(len(texts), index + 4)):
                    candidate = texts[next_idx]
                    if candidate and not looks_like_label(candidate):
                        candidate_val = candidate.strip()
                        if join_uppercase_lines and candidate_val.isupper():
                            for follow_idx in range(next_idx + 1, min(len(texts), next_idx + 3)):
                                follow_line = texts[follow_idx].strip()
                                if follow_line.isupper() and not looks_like_label(follow_line):
                                    candidate_val += " " + follow_line
                                else:
                                    break
                        return normalize_spaces(candidate_val)
    return ""


def find_date_near(texts: list[str], labels: list[str], allow_global: bool = False) -> str:
    for index, text in enumerate(texts):
        comparable = strip_accents_for_match(text).lower()
        if any(strip_accents_for_match(label).lower() in comparable for label in labels):
            start_idx = max(0, index - 3)
            end_idx = min(len(texts), index + 5)
            local = "\n".join(texts[start_idx : end_idx])
            date = first_date(local)
            if date:
                return date
    return first_date("\n".join(texts)) if allow_global else ""


def find_gender(texts: list[str]) -> str:
    joined = "\n".join(texts)
    normalized = strip_accents_for_match(joined).lower()
    if re.search(r"\bnu\b", normalized):
        return "Nữ"
    if re.search(r"\bnam\b", normalized):
        return "Nam"
    return ""


def match_label(text: str, keys: list[str]) -> bool:
    normalized_text = strip_accents_for_match(text).lower()
    for key in keys:
        norm_key = strip_accents_for_match(key).lower()
        if norm_key in normalized_text:
            return True
            
    # Fuzzy matching for common typos in Vietnamese CCCD labels
    text_clean = re.sub(r'[^a-z0-9]', '', normalized_text)
    if "thuong tru" in keys or "noi thuong tru" in keys:
        if "thuongtru" in text_clean or "thugtru" in text_clean or "thungtru" in text_clean or "thugtr" in text_clean or "thumgtru" in text_clean:
            return True
        if any(w in normalized_text for w in ["residen", "esiden", "sidenc", "fesidenc", "fesiden"]):
            return True
    if any(k in keys for k in ["Nơi cư trú", "Noi cu tru", "Place of residence"]):
        if any(w in text_clean for w in ["cutru", "noicutru", "cuitru", "noicuitru", "cuuru", "noicuuru"]):
            return True
        if any(w in normalized_text for w in [
            "residen", "esiden", "sidenc", "residence", "piace", "place", "cutru", "cu tru", "cuitru",
            "cuuru", "ssidon", "ssidonca", "picepf"
        ]):
            return True
    if any(k in keys for k in ["Nơi đăng ký khai sinh", "Noi dang ky khai sinh", "Place of birth"]):
        if any(w in normalized_text for w in ["khai sinh", "khaisinh", "birth", "bith", "brth", "sinh", "sing", "dang ky", "dangky"]):
            return True
        if any(w in text_clean for w in ["khaisinh", "dangky", "thalsinh", "chaisinh", "chalsinh"]):
            return True
    if "que quan" in keys:
        if "quequan" in text_clean or "qquan" in text_clean or "origin" in normalized_text:
            return True
    if "co gia tri" in keys or "date of expiry" in keys:
        if "cogiatri" in text_clean or "giatri" in text_clean or "expiry" in normalized_text or "expir" in normalized_text:
            return True
    return False


def clean_start_line(text: str) -> str:
    # Nếu dòng chứa nhãn có dấu hai chấm `:`, thường phần giá trị nằm sau dấu hai chấm
    if ":" in text:
        parts = text.split(":", 1)
        # Chỉ lấy phần sau dấu hai chấm nếu phần trước chứa các từ khóa nhãn phổ biến
        prev = strip_accents_for_match(parts[0]).lower()
        if any(w in prev for w in ["noi", "cu", "tru", "place", "residence", "origin", "dang", "ky", "khai", "sinh", "birth"]):
            return parts[1].strip()
            
    # Nếu không có dấu hai chấm, hãy tìm các mảnh từ nhãn tiếng Anh phổ biến để cắt bỏ
    normalized = strip_accents_for_match(text).lower()
    for kw in [
        "residence", "residenoe", "residen", "fesidenc", "fesiden", "esiden", "rosidanca", "residanca",
        "piaceci", "piace", "place", "pme", "pwncuo", "eskionce",
        "dang ky", "khai sinh", "cu tru", "cuitru", "cutru", "cuiru", "birth", "bith", "origin"
    ]:
        if kw in normalized:
            idx = normalized.find(kw)
            # Cắt bỏ toàn bộ phần nhãn phía trước kèm các ký tự đặc biệt
            rest = text[idx + len(kw):].strip(" :-/|.,_}")
            # Nếu phần còn lại vẫn chứa nhãn tiếng Anh khác hoặc từ rác, tiếp tục làm sạch đệ quy
            return clean_start_line(rest)
            
    return text


def collect_between(texts: list[str], start_labels: list[str], end_labels: list[str], max_lines: int = None) -> str:
    start = None
    end = None

    for index, text in enumerate(texts):
        if start is None and match_label(text, start_labels):
            start = index
            continue
        if start is not None and match_label(text, end_labels):
            end = index
            break
            
    if start is None:
        # Fallback: if header is missing/misread, extract lines that contain typical address keywords
        address_indicators = ["tinh", "thanh pho", "tp.", "huyen", "quan", "xa ", "phuong", "duong", " thon ", " ap ", " so "]
        address_lines = []
        for text in texts:
            norm = strip_accents_for_match(text).lower()
            if any(skip in norm for skip in [
                "cong hoa", "xa hoi", "doc lap", "tu do", "hanh phuc", 
                "gioi tinh", "gioi tnh", "sex", "gender", "nam", "nu", 
                "ngay sinh", "nam sinh", "birth", "bith", "date", 
                "quoc tich", "nationality", "so cccd", "so dinh danh", "so / no", "identity"
            ]):
                continue
            if any(ind in norm for ind in address_indicators):
                address_lines.append(text)
        if address_lines:
            return normalize_spaces(", ".join(address_lines[:max_lines] if max_lines else address_lines))
        return ""

    labels_to_remove = start_labels + end_labels
    limit_end = end if end is not None else len(texts)
    if max_lines is not None:
        limit_end = min(limit_end, start + max_lines + 1)
        
    raw_values = texts[start : limit_end]
    values = []
    
    if raw_values:
        # Làm sạch đặc biệt cho dòng đầu tiên (chứa nhãn bắt đầu) để loại bỏ nhãn bị lỗi OCR
        first_line = clean_start_line(raw_values[0])
        cleaned = remove_known_labels(first_line, labels_to_remove).strip(" :-/|.,_}")
        if cleaned and not looks_like_label(cleaned):
            values.append(cleaned)
            
        # Các dòng tiếp theo xử lý bình thường
        for part in raw_values[1:]:
            cleaned = remove_known_labels(part, labels_to_remove).strip(" :-/|.,_}")
            if cleaned and not looks_like_label(cleaned):
                values.append(cleaned)
                
    value = normalize_spaces(", ".join(values))
    return value


def first_date(text: str) -> str:
    if not text:
        return ""
    
    def clean_digits(s: str) -> str:
        s = s.replace('O', '0').replace('o', '0').replace('d', '0').replace('D', '0')
        s = s.replace('I', '1').replace('i', '1').replace('l', '1')
        return s
        
    normalized = strip_accents_for_match(text).lower()
    
    # 1. Pattern: ngay DD thang MM nam YYYY (Vietnamese word dates)
    pattern_words = re.compile(r"ngay\s*([0-9ooddiil]{1,2})\s*thang\s*([0-9ooddiil]{1,2})\s*nam\s*([0-9ooddiil]{4})")
    match_words = pattern_words.search(normalized)
    if match_words:
        day = clean_digits(match_words.group(1))
        month = clean_digits(match_words.group(2))
        year = clean_digits(match_words.group(3))
        try:
            return f"{int(day):02d}/{int(month):02d}/{year}"
        except ValueError:
            pass
            
    # 2. Pattern: DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY (with optional spaces around separators)
    pattern_slashes = re.compile(r"\b([0-9ooddiil]{1,2})\s*[./-]\s*([0-9ooddiil]{1,2})\s*[./-]\s*([0-9ooddiil]{4})\b")
    match_slashes = pattern_slashes.search(normalized)
    if match_slashes:
        day = clean_digits(match_slashes.group(1))
        month = clean_digits(match_slashes.group(2))
        year = clean_digits(match_slashes.group(3))
        try:
            return f"{int(day):02d}/{int(month):02d}/{year}"
        except ValueError:
            pass
            
    # 3. Fallback to raw digit sequence without separators (e.g. 24032003)
    digits = re.search(r"\b([0-9ooddiil]{2})([0-9ooddiil]{2})([0-9ooddiil]{4})\b", normalized)
    if digits:
        day = clean_digits(digits.group(1))
        month = clean_digits(digits.group(2))
        year = clean_digits(digits.group(3))
        try:
            return f"{int(day):02d}/{int(month):02d}/{year}"
        except ValueError:
            pass
            
    return ""



def normalize_date(value: str) -> str:
    value = normalize_spaces(value)
    date = first_date(value)
    return date or value


def normalize_gender(value: str) -> str:
    key = strip_accents_for_match(value).lower()
    if "nu" in key:
        return "Nữ"
    if "nam" in key or key == "m":
        return "Nam"
    return value


def title_case_name(value: str) -> str:
    value = normalize_spaces(value)
    if value.isupper():
        return " ".join(part.capitalize() for part in value.split(" "))
    return value


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def looks_like_label(value: str) -> bool:
    key = strip_accents_for_match(value).lower()
    # Check for common OCR fragments of labels
    bad_words = [
        "full name", "ho va ten", "ho va ten", "he va ten", "he va ten", "nanve", "vaten", "ho ya ten", "hoyaten", "hoaten", "hoten", "ho ya ten", "ho ya ten",
        "date of birth", "ngay sinh", "ngay, thang, nam sinh", "bith", "slnh", "birth",
        "gioi tinh", "sex", "gender", "gioi tnh",
        "quoc tich", "nationality", "nauonality", "nanonality",
        "que quan", "place of origin", "place ofongln", "place of", "ofongln",
        "thuong tru", "noi thuong tru", "place of residence", "fesidence", "placc",
        "date of expiry", "co gia tri", "gia tri den", "den ngay", "ngay het han",
        "so / no", "so cccd", "citizen identity", "citizen", "identity", "card",
        "doc lap", "tu do", "hanh phuc", "cong hoa", "viet nam",
        "khai sinh", "chu dem", "ten khai sinh", "ho, chu dem"
    ]
    return any(w in key for w in bad_words)


def remove_known_labels(value: str, labels: list[str]) -> str:
    result = value
    normalized_labels = set(labels)
    normalized_labels.update(strip_accents_for_match(label) for label in labels)
    for label in sorted(normalized_labels, key=len, reverse=True):
        result = re.sub(re.escape(label), "", result, flags=re.IGNORECASE)
    return result


def strip_accents_for_match(value: str) -> str:
    replacements = {
        "à": "a",
        "á": "a",
        "ả": "a",
        "ã": "a",
        "ạ": "a",
        "ă": "a",
        "ằ": "a",
        "ắ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "ặ": "a",
        "â": "a",
        "ầ": "a",
        "ấ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ậ": "a",
        "đ": "d",
        "è": "e",
        "é": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ẹ": "e",
        "ê": "e",
        "ề": "e",
        "ế": "e",
        "ể": "e",
        "ễ": "e",
        "ệ": "e",
        "ì": "i",
        "í": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ị": "i",
        "ò": "o",
        "ó": "o",
        "ỏ": "o",
        "õ": "o",
        "ọ": "o",
        "ô": "o",
        "ồ": "o",
        "ố": "o",
        "ổ": "o",
        "ỗ": "o",
        "ộ": "o",
        "ơ": "o",
        "ờ": "o",
        "ớ": "o",
        "ở": "o",
        "ỡ": "o",
        "ợ": "o",
        "ù": "u",
        "ú": "u",
        "ủ": "u",
        "ũ": "u",
        "ụ": "u",
        "ư": "u",
        "ừ": "u",
        "ứ": "u",
        "ử": "u",
        "ữ": "u",
        "ự": "u",
        "ỳ": "y",
        "ý": "y",
        "ỷ": "y",
        "ỹ": "y",
        "ỵ": "y",
    }
    return "".join(replacements.get(ch, replacements.get(ch.lower(), ch)) for ch in value)


def merge_missing(target: dict[str, str], source: dict[str, str]) -> None:
    for key, value in source.items():
        if value and not target.get(key):
            target[key] = value


def merge_ocr_data(target: dict[str, str], source: dict[str, str]) -> None:
    for key, value in source.items():
        if not value:
            continue
        if not target.get(key):
            target[key] = value
            continue
        if key in {"ho_va_ten", "que_quan", "noi_thuong_tru"} and has_vietnamese_accent(value) and not has_vietnamese_accent(target[key]):
            target[key] = value


def has_vietnamese_accent(value: str) -> bool:
    return strip_accents_for_match(value) != value


def save_result(result: dict[str, Any], result_dir: Path) -> None:
    json_path = result_dir / "result.json"
    csv_path = result_dir / "result.csv"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(result["data"])
