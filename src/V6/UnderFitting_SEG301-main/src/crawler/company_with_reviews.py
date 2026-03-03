import json
import torch
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz
from tqdm import tqdm

# =====================
# CẤU HÌNH
# =====================
COMPANY_FILE = "Data_doanh_nghiep.jsonl"      # file lớn (JSONL)
REVIEW_FILE  = "1900_merged.json"        # file nhỏ (JSON)
OUTPUT_FILE  = "company_with_reviews.jsonl"
LOG_FILE     = "matched_logs.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SIM_THRESHOLD = 0.90
FUZZY_THRESHOLD = 90
BATCH_SIZE = 2048

print("DEVICE:", DEVICE)

# =====================
# HÀM CHUẨN HÓA
# =====================
def normalize(s):
    if not isinstance(s, str):
        return ""
    return (
        s.lower()
        .replace("★", " ")
        .replace("-", " ")
        .strip()
    )

# =====================
# LOAD COMPANY (JSONL)
# =====================
companies = []
with open(COMPANY_FILE, "r", encoding="utf-8") as f:
    for line in f:
        companies.append(json.loads(line))

print("Total companies:", len(companies))

# =====================
# LOAD REVIEW (JSON)
# =====================
with open(REVIEW_FILE, "r", encoding="utf-8") as f:
    reviews = json.load(f)

print("Total reviews:", len(reviews))

# =====================
# LOAD MODEL
# =====================
model = SentenceTransformer(MODEL_NAME, device=DEVICE)

# =====================
# ENCODE REVIEW (NHỎ)
# =====================
review_names = [normalize(r.get("company_name", "")) for r in reviews]

review_emb = model.encode(
    review_names,
    convert_to_tensor=True,
    normalize_embeddings=True,
    batch_size=256,
    show_progress_bar=True
)

# =====================
# GHÉP + LOG
# =====================
matched_logs = []

for i in tqdm(range(0, len(companies), BATCH_SIZE)):
    batch = companies[i:i + BATCH_SIZE]

    batch_names = [
        normalize(c.get("Tên doanh nghiệp", ""))
        for c in batch
    ]

    batch_emb = model.encode(
        batch_names,
        convert_to_tensor=True,
        normalize_embeddings=True,
        batch_size=256
    )

    scores = util.cos_sim(batch_emb, review_emb)

    for idx, company in enumerate(batch):
        company_name = batch_names[idx]
        if not company_name:
            continue

        best_score, best_idx = torch.max(scores[idx], dim=0)
        best_score = float(best_score)

        if best_score < SIM_THRESHOLD:
            continue

        review_name = review_names[best_idx]
        fuzzy_score = fuzz.token_set_ratio(company_name, review_name)

        if fuzzy_score < FUZZY_THRESHOLD:
            continue

        review_obj = {
            **reviews[best_idx],
            "semantic_score": best_score,
            "fuzzy_score": fuzzy_score
        }

        company.setdefault("reviews", []).append(review_obj)

        log = {
            "company_name": company.get("Tên doanh nghiệp", ""),
            "review_company_name": reviews[best_idx].get("company_name", ""),
            "semantic_score": best_score,
            "fuzzy_score": fuzzy_score
        }

        matched_logs.append(log)

        # ===== IN RA MÀN HÌNH =====
        print(
            f"[MATCH] {log['company_name']}  <--->  "
            f"{log['review_company_name']} | "
            f"sim={best_score:.3f}, fuzzy={fuzzy_score}"
        )

# =====================
# GHI FILE OUTPUT (JSONL)
# =====================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for c in companies:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

# =====================
# GHI LOG GHÉP
# =====================
with open(LOG_FILE, "w", encoding="utf-8") as f:
    json.dump(matched_logs, f, ensure_ascii=False, indent=2)

# =====================
# TỔNG KẾT
# =====================
print("\n===== SUMMARY =====")
print("Total matched:", len(matched_logs))
print("Output file:", OUTPUT_FILE)
print("Log file:", LOG_FILE)
