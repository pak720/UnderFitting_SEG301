# XÓA DUPLICATES

import pandas as pd

# Đọc dữ liệu
df = pd.read_csv("Data_infodoanhnghiep.csv", encoding="utf-8-sig")

# Xóa dòng trùng theo các cột index 0, 2, 3 (giữ dòng đầu tiên)
df = df.drop_duplicates(subset=df.columns[[0, 2, 3]], keep="first")

# Reset index (khuyến nghị)
df.reset_index(drop=True, inplace=True)

# Ghi lại vào file mới
df.to_csv("Data_infodoanhnghiep_clean.csv", index=False, encoding="utf-8-sig")

# Kiểm tra nhanh
df.info()

