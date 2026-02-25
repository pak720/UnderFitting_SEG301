"""Text preprocessing module for indexing"""
import re
import unicodedata
from typing import List, Set


class TextPreprocessor:
    """Handles text preprocessing for indexing and search"""

    def __init__(self):
        # Vietnamese stopwords
        self.stopwords = {
            'và', 'để', 'là', 'của', 'do', 'được', 'tại', 'từ', 'vào', 'với',
            'có', 'cái', 'cần', 'các', 'như', 'thì', 'hoặc', 'nhưng', 'hay',
            'nếu', 'khi', 'mà', 'cũng', 'lại', 'hơn', 'trong', 'trên', 'dưới',
            'chỉ', 'bao', 'xung', 'quanh', 'nhân', 'lên', 'xuống', 'ra', 'vào',
            'qua', 'một', 'mấy', 'những', 'những', 'cây', 'chiếc', 'chuỗi',
            'nước', 'mỗi', 'tất', 'cả', 'nhiều', 'ít', 'toàn', 'bộ', 'phần',
            'rất', 'quá', 'tương', 'đối', 'gần', 'xa', 'đủ', 'khoảng'
        }

    def normalize_text(self, text: str) -> str:
        """Normalize Vietnamese text"""
        if not text:
            return ""

        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # Normalize unicode (decompose diacritics then recompose)
        text = unicodedata.normalize('NFKD', text)

        # Convert to lowercase
        text = text.lower()

        return text

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        text = self.normalize_text(text)

        # Remove special characters but keep Vietnamese characters
        text = re.sub(r'[^\w\sàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỵỷỸỹ]+', ' ', text)

        # Split by whitespace
        tokens = text.split()

        return tokens

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove stopwords from token list"""
        return [token for token in tokens if token not in self.stopwords and len(token) > 1]

    def process(self, text: str, remove_stops: bool = True) -> List[str]:
        """Full preprocessing pipeline"""
        tokens = self.tokenize(text)
        if remove_stops:
            tokens = self.remove_stopwords(tokens)
        return tokens


def extract_searchable_text(doc: dict) -> str:
    """Extract searchable text from a document"""
    # Combine all fields for indexing
    searchable_fields = [
        'Tên doanh nghiệp',
        'Tên giao dịch',
        'Địa chỉ',
        'Ngành nghề kinh doanh',
        'Cơ quan thuế',
        'Mã số thuế'
    ]

    texts = []
    for field in searchable_fields:
        if field in doc and doc[field]:
            texts.append(str(doc[field]))

    return ' '.join(texts)
