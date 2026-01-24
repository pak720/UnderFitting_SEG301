import json
import re
from unidecode import unidecode
from rapidfuzz import fuzz

# =========================
# CONFIG
# =========================
FILE1_PATH = "Data_doanh_nghiep_v2.jsonl"
FILE2_PATH = "1900_merged.json"
OUTPUT_PATH = "merged.jsonl"

MATCH_THRESHOLD = 83


# =========================
# UTILS
# =========================
def normalize_text(text: str) -> str:
    text = unidecode(text.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_substring_match(a: str, b: str) -> bool:
    """
    Bắt buộc 1 trong 2 chuỗi phải chứa chuỗi còn lại
    """
    return a in b or b in a


def similarity(a: str, b: str) -> float:
    """
    Dùng ratio thay vì token_set_ratio (chặt hơn)
    """
    return fuzz.ratio(a, b)


# =========================
# LOAD FILE 2 (JSON)
# =========================
with open(FILE2_PATH, "r", encoding="utf-8") as f:
    data2 = json.load(f)

normalized_data2 = [
    {
        "raw": row,
        "norm_name": normalize_text(row.get("company_name", ""))
    }
    for row in data2
]


# =========================
# PROCESS FILE 1 (JSONL)
# =========================
with open(FILE1_PATH, "r", encoding="utf-8") as fin, \
     open(OUTPUT_PATH, "w", encoding="utf-8") as fout:

    for line in fin:
        row1 = json.loads(line)

        name1_raw = row1.get("Tên doanh nghiệp", "")
        name1 = normalize_text(name1_raw)

        best_match = None
        best_score = 0

        for item in normalized_data2:
            name2 = item["norm_name"]

            # 🔒 Điều kiện 1: substring bắt buộc
            if not is_substring_match(name1, name2):
                continue

            score = similarity(name1, name2)

            if score > best_score:
                best_score = score
                best_match = item["raw"]

        # Merge nếu đủ điều kiện
        if best_match and best_score >= MATCH_THRESHOLD:
            for k, v in best_match.items():
                if k not in row1:
                    row1[k] = v

            row1["_match_score"] = best_score
            row1["_matched_company_name"] = best_match.get("company_name")

        fout.write(json.dumps(row1, ensure_ascii=False) + "\n")

print("✅ Merge xong – đã chặn false positive")
