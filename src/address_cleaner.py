import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

class AddressCleaner:
    """
    Công cụ cải thiện dữ liệu địa chỉ từ crawl web
    Xử lý 3 vấn đề chính:
    1. Loại bỏ dấu phẩy thừa (,,)
    2. Gộp số nhà với tên đường (không phân tách bằng dấu phẩy)
    3. Xử lý số nhà có ký tự (80A thay vì 80 A)
    """
    
    ADMIN_KEYWORDS = [
        'Phường', 'Xã', 'Tỉnh', 'Quận', 'Thành phố', 'TX', 'TT', 
        'Huyện', 'TP', 'Thị xã', 'Thị trấn', 'Khu phố', 'Tổ dân phố',
        'Việt Nam', 'Vietnam'
    ]
    
    def __init__(self):
        self.stats = {
            'total': 0,
            'removed_double_comma': 0,
            'merged_house_street': 0,
            'fixed_house_char': 0,
            'improved': 0
        }
    
    @staticmethod
    def is_admin_component(text: str) -> bool:
        """Kiểm tra xem có phải là thành phần hành chính không"""
        return any(keyword in text for keyword in AddressCleaner.ADMIN_KEYWORDS)
    
    @staticmethod
    def is_house_number(text: str) -> bool:
        """
        Kiểm tra xem có phải là số nhà không
        VD: "22", "226", "25-1", "80A", "25/4", "02"
        """
        text = text.strip()
        patterns = [
            r'^[\d]+[A-Z]?$',                      # "22", "80A"
            r'^[\d]+\s*-\s*[\d]+[A-Z]?$',          # "25-1", "25 - 1"
            r'^[\d]+\s*/\s*[\d]+[A-Z]?$',          # "25/4"
            r'^[\d]+\s*-\s*Lý\s+Thái\s+Tổ',        # "25 - Lý Thái Tổ" (Lần này là số nhà)
        ]
        return any(re.match(pattern, text) for pattern in patterns)
    
    def clean_address(self, address: str) -> str:
        """
        Cải thiện dữ liệu địa chỉ theo định dạng tiêu chuẩn Việt Nam
        Format: [Số nhà/Lô] [Tên đường], [Phường/Xã], [Quận/Huyện], [Thành phố/Tỉnh], [Quốc gia]
        
        Args:
            address: Chuỗi địa chỉ gốc
            
        Returns:
            Chuỗi địa chỉ đã cải thiện
        """
        if not address or not isinstance(address, str):
            return address
        
        original = address
        self.stats['total'] += 1

        # Chuẩn hóa khoảng trắng thừa
        address = re.sub(r'\s+', ' ', address).strip()

        # Sửa các từ bị tách sai phổ biến
        address = re.sub(r'\bKhu\s+ất\b', 'Khuất', address, flags=re.IGNORECASE)
        
        # Bước 1: Loại bỏ dấu phẩy thừa (,, -> ,)
        had_double_comma = ',,' in address
        if had_double_comma:
            address = re.sub(r',+', ',', address)
            self.stats['removed_double_comma'] += 1
        
        address = address.strip(',').strip()
        
        # Bước 2: Xử lý toàn diện số nhà - áp dụng cho TẤT CẢ các format
        # =============================================================
        
        # Bước 2.0: Chuẩn hóa format (GIỮ nguyên "Số nhà" prefix)
        # Chỉ xóa "SN" vì nó là viết tắt không rõ nghĩa
        address = re.sub(r'\bSN\s+', '', address)
        address = re.sub(r',(?=[^\s])', ', ', address)  # Thêm khoảng trắng sau dấu phẩy nếu không có
        address = re.sub(r'\s{2,}', ' ', address).strip()
        
        # Hàm tổng quát để chuẩn hóa số nhà
        def _normalize_house_numbers(addr: str) -> str:
            """
            Chuẩn hóa số nhà theo các rule áp dụng cho TẤT CẢ format:
            1. Loại bỏ khoảng trắng giữa số và ký tự: "5 C/1" -> "5C/1"
            2. Loại bỏ khoảng trắng giữa ký tự+số và số khác: "25C 5" -> "25C/5"
            3. Gộp các số liên tiếp cách bằng khoảng trắng: "29 31" -> "29-31"
            4. Gộp các số có dấu phẩy: "29 31, 33" -> "29-31-33"
            5. Xử lý kết hợp: "76/29 31, 33" -> "76/29-31-33"
            """
            result = addr
            
            # Rule 1: Loại bỏ khoảng trắng giữa số và ký tự (5 C/1 -> 5C/1)
            result = re.sub(r'(\d+)\s+([A-Z])(/\d+)', r'\1\2\3', result)
            
            # Rule 1.5: Loại bỏ khoảng trắng giữa số và ký tự CUỐI CÙNG (quốc lộ 1 A -> quốc lộ 1A)
            result = re.sub(r'(\d+)\s+([A-Z])(?=\s*[,.]|\s*$)', r'\1\2', result)
            
            # Rule 2: Gộp số+ký tự với số tiếp theo (25C 5 -> 25C/5)
            result = re.sub(r'(\d+[A-Z])\s+(\d+)(?=\s*[,\s])', r'\1/\2', result)
            
            # Rule 3 & 4 & 5: Xử lý toàn bộ địa chỉ - không tách house_part/street_part
            # Vì tách sẽ bỏ mất dấu phẩy và dấu cách. Thay vào đó xử lý trực tiếp
            max_iterations = 10
            iteration = 0
            prev_result = ""
            
            while prev_result != result and iteration < max_iterations:
                prev_result = result
                iteration += 1
                
                # Thay dấu phẩy + số bằng hyphen hoặc slash tùy theo ký tự trước dấu phẩy
                # "29, 31" -> "29-31" (số thuần -> hyphen)
                # "25C, 5 Lý..." -> "25C/5, Lý..." (số+chữ -> slash + giữ comma cho phần sau)
                result = re.sub(r'([A-Z]),\s*(\d)', r'\1/\2, ', result)  # Chữ cái + dấu phẩy + số -> slash + comma
                result = re.sub(r'(\d),\s*(?=\d)', r'\1-', result)       # Số + dấu phẩy + số -> hyphen
                
                # Gộp các số cách nhau bằng khoảng trắng
                result = re.sub(
                    r'\b(\d+(?:[A-Z])?(?:/\d+)?(?:/[A-Z]\d+)?(?:-\d+)*)\s+(\d+)(?=\s*[-,A-Za-zĐđĂăÂâÊêÔôƠơƯư])',
                    r'\1-\2',
                    result
                )
            
            return result
        
        address = _normalize_house_numbers(address)

        # Bước 2.2: Xử lý ký hiệu lô/ô/điểm dạng "D 10" -> "D10" hoặc "A 2" -> "A2"
        # Ví dụ: "D 10 Khuất Duy Tiến" -> "D10 Khuất Duy Tiến"
        #         "Lô A 2" -> "Lô A2", "CN 1" -> "CN1"
        # Nhưng giữ nguyên "Lô A 4 Khu..." để gộp theo đúng format
        def _merge_letter_number(match: re.Match) -> str:
            prefix = match.group(1)
            number = match.group(2)
            # Giữ nguyên các tiền tố không nên gộp như "SN"
            if prefix in {"SN"}:
                return f"{prefix} {number}"
            return f"{prefix}{number}"

        address = re.sub(
            r'\b([A-Z]{1,3})\s+(\d+)\b',
            _merge_letter_number,
            address
        )

        # Bước 2.2: Loại bỏ ký hiệu phường viết tắt nếu đã có "Phường" đầy đủ
        # Ví dụ: "5 Sư Thiện Chiếu P.07, Phường 07" -> "5 Sư Thiện Chiếu, Phường 07"
        if re.search(r'\bPhường\s*0?\d+\b', address, flags=re.IGNORECASE):
            address = re.sub(r'\s*P\.\s*0?\d+\b\s*,?\s*', ' ', address, flags=re.IGNORECASE)
            address = re.sub(r'\s+,', ',', address)
            address = re.sub(r',\s*,', ',', address)
            address = re.sub(r'\s{2,}', ' ', address).strip(' ,')
        
        # Bước 3: Xử lý gộp Lô/Số nhà + Tên khu/đường
        # Pattern: Lô [A-Z0-9]+ [Khu/Đường/Phố...] hoặc Số [A-Z0-9]+ [Tên đường]
        address = self._merge_lot_with_location(address)
        
        # Bước 4: Gộp số nhà với tên đường thông minh (qua dấu phẩy)
        parts = address.split(',')
        result_parts = []
        i = 0
        
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue
            
            # Nếu phần hiện tại là số nhà có ký hiệu (vd: 80A, 25/4, 25-1)
            # thì gộp với phần tiếp theo (không gộp số thuần như "04" để giữ format "04, Tên đường")
            if self.is_house_number(part) and i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                is_pure_number = re.match(r'^\d+$', part) is not None
                has_suffix = re.search(r'[A-Za-z]', part) is not None
                has_separator = ('/' in part) or ('-' in part)

                if next_part and not self.is_admin_component(next_part) and (has_suffix or has_separator) and not is_pure_number:
                    # Gộp số nhà với tên đường (GIỮ dấu phẩy!)
                    result_parts.append(part + ', ' + next_part)
                    self.stats['merged_house_street'] += 1
                    i += 2
                    continue

                # Trường hợp số thuần bị tách do dấu phẩy thừa: "04, Nguyên Tất Thành,, ..."
                if had_double_comma and is_pure_number and next_part and not self.is_admin_component(next_part):
                    result_parts.append(part + ', ' + next_part)
                    self.stats['merged_house_street'] += 1
                    i += 2
                    continue
            
            result_parts.append(part)
            i += 1
        
        final_address = ', '.join(result_parts)
        
        # Kiểm tra xem có cải thiện không
        if final_address != original:
            self.stats['improved'] += 1
        
        return final_address
    
    def _merge_lot_with_location(self, address: str) -> str:
        """
        Gộp Lô/Số + Khu/Đường lại với nhau (không qua dấu phẩy)
        Ví dụ: "Lô A 4 Khu Công Nghiệp Lộc Sơn, Phường..."
               -> "Lô A4 Khu Công Nghiệp Lộc Sơn, Phường..."
        
        Xử lý các pattern:
        - "Lô [A-Z]+ [0-9]+ [Khu/Đường/Phố...]"
        - "Số [0-9]+ [Đường/Phố...]"
        """
        # Pattern 1: Lô A 4 Khu... -> Lô A4 Khu...
        # Tìm "Lô [chữ] [số] [chữ khu/đường...]"
        address = re.sub(
            r'\bLô\s+([A-Z0-9]+)\s+(\d+)\s+(Khu|Đường|Phố|Ngõ|Hẻm|Phục)',
            r'Lô \1\2 \3',
            address,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: Số 25 Đường... -> Số 25 Đường... (giữ nguyên vì đã đúng)
        # Nhưng xử lý "Số 25 Tên đường phức tạp"
        
        return address
    
    def process_file(self, input_path: str, output_path: str) -> int:
        """
        Đọc file JSONL, xử lý cột địa chỉ, và lưu ra file mới
        
        Args:
            input_path: Đường dẫn file JSONL gốc
            output_path: Đường dẫn file JSONL kết quả
            
        Returns:
            Tổng số bản ghi đã xử lý
        """
        with open(input_path, 'r', encoding='utf-8') as f_in:
            lines = f_in.readlines()
        
        cleaned_lines = []
        
        for line in lines:
            try:
                record = json.loads(line)
                
                if 'Địa chỉ' in record:
                    record['Địa chỉ'] = self.clean_address(record['Địa chỉ'])
                
                cleaned_lines.append(json.dumps(record, ensure_ascii=False))
            except json.JSONDecodeError as e:
                print(f"Lỗi đọc dòng: {e}")
                cleaned_lines.append(line.strip())
        
        # Lưu kết quả
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for line in cleaned_lines:
                f_out.write(line + '\n')
        
        return len(cleaned_lines)
    
    def show_comparison(self, input_path: str, num_samples: int = 10):
        """
        Hiển thị so sánh trước/sau của một số bản ghi
        
        Args:
            input_path: Đường dẫn file JSONL gốc
            num_samples: Số lượng mẫu cần hiển thị
        """
        print("\n" + "="*100)
        print("SO SÁNH TRƯỚC/SAU XỬ LÝ".center(100))
        print("="*100 + "\n")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        count = 0
        for line in lines:
            if count >= num_samples:
                break
            
            try:
                record = json.loads(line)
                original = record.get('Địa chỉ', '')
                company = record.get('Tên doanh nghiệp', '')
                cleaned = self.clean_address(original)
                
                if original != cleaned:
                    count += 1
                    print(f"#{count} - {company}")
                    print(f"  TRƯỚC:  {original}")
                    print(f"  SAU:    {cleaned}")
                    print()
            except json.JSONDecodeError:
                continue
    
    def print_stats(self):
        """In thống kê xử lý"""
        print("\n" + "="*100)
        print("THỐNG KÊ XỬ LÝ".center(100))
        print("="*100)
        print(f"Tổng số bản ghi xử lý:        {self.stats['total']}")
        print(f"Loại bỏ dấu phẩy thừa:       {self.stats['removed_double_comma']}")
        print(f"Gộp số nhà với tên đường:    {self.stats['merged_house_street']}")
        print(f"Sửa số nhà có ký tự (80A):   {self.stats['fixed_house_char']}")
        print(f"Tổng bản ghi được cải thiện: {self.stats['improved']}")
        print("="*100 + "\n")


def main():
    """Hàm chính"""
    input_file = Path("D:\\final_merged_3.jsonl")
    output_file = Path("D:\\final_merged_3_cleaned.jsonl")
    
    # Tạo instance
    cleaner = AddressCleaner()
    
    # Hiển thị so sánh trước/sau
    cleaner.show_comparison(str(input_file), num_samples=15)
    
    # Xử lý file
    total = cleaner.process_file(str(input_file), str(output_file))
    
    print(f"✓ Đã xử lý xong!")
    print(f"  File gốc:  {input_file}")
    print(f"  File kết quả: {output_file}")
    
    # In thống kê
    cleaner.print_stats()


if __name__ == "__main__":
    main()

    # Test case cho xử lý 2 số nhà cách nhau
    print("\n" + "="*100)
    print("TEST XỬ LÝ 2 SỐ NHÀ CÁCH NHAU".center(100))
    print("="*100 + "\n")
    
    test_cases = [
        "29 31 Đinh Bộ Lĩnh P.24, Quận Bình Thạnh, TP Hồ Chí Minh",
        "5 7 Nguyễn Huệ, Quận 1, TP Hồ Chí Minh",
        "12 14 16 Lê Thánh Tông, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh",
        "Lô A 2 Khu Công Nghiệp, Phường Tân Phú",
        "100 102 Phan Xích Long, Phường 2, Quận Phú Nhuận, TP Hồ Chí Minh",
        # Các trường hợp mới
        "29 31, 33 Nguyễn Văn Trỗi P.12, Quận Phú Nhuận, TP Hồ Chí Minh",
        "76/29 31, 33 Bà Hom, Phường 13, Quận 6, TP Hồ Chí Minh",
        "10 12, 14, 16 Lê Lợi, Quận Hoàn Kiếm, Hà Nội",
        "88/25 27, 29, 31 Nguyễn Trãi, Phường Bến Thành, Quận 1, TP Hồ Chí Minh",
        # Các trường hợp với ký tự và dấu /
        "5 C/1 Nguyễn Oanh, Phường 17, Quận Gò Vấp, TP Hồ Chí Minh",
        "25C 5 Chu Văn An P.26, Quận Bình Thạnh, TP Hồ Chí Minh",
        "3 B/4 Lý Thái Tổ, Hoàn Kiếm, Hà Nội",
        "12A 7 Nguyễn Hữu Cảnh, Quận Bình Thạnh, TP Hồ Chí Minh",
    ]
    
    cleaner = AddressCleaner()
    for test in test_cases:
        result = cleaner.clean_address(test)
        if result != test:
            print(f"✓ TRƯỚC:  {test}")
            print(f"  SAU:    {result}")
            print()
