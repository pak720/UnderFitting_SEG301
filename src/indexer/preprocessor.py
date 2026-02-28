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

        # Industry/domain phrase dictionary for segmentation.
        # We convert common multi-word terms into one token (joined by "_")
        # so BM25 can match domain intent more accurately.
        # Example: "dệt may" -> "dệt_may", "điện lực" -> "điện_lực".
        self.industry_phrases = {
            # Textile / Fabric
            'dệt may', 'sợi dệt', 'vải dệt', 'vải không dệt', 'nhuộm vải',
            'may mặc', 'nguyên phụ liệu', 'phụ liệu may mặc', 'công nghiệp dệt may',
            # Electric / Energy
            'điện lực', 'điện năng', 'thiết bị điện', 'cơ điện', 'năng lượng',
            'năng lượng tái tạo', 'điện mặt trời', 'điện gió',
            'điện tử', 'linh kiện điện tử', 'thiết bị điện tử', 'điện gia dụng', 'đồ điện gia dụng',
            'điện lạnh',
            # Tech / IT
            # Add both short and long forms so query "công nghệ" is not split into
            # generic tokens "công" + "nghệ".
            'công nghệ', 'công nghệ thông tin', 'phần mềm', 'dữ liệu lớn',
            # Medical / Pharma
            'trang thiết bị y tế', 'dược phẩm', 'y tế', 'phòng khám',
            # Logistics / Transport
            'vận tải', 'kho bãi',
            # Construction
            'xây dựng', 'vật liệu xây dựng',
            # Finance
            'tài chính', 'ngân hàng', 'bảo hiểm',
            # Commerce
            'bán lẻ', 'bán buôn',
            # Food / F&B
            'thực phẩm', 'ăn uống', 'dịch vụ ăn uống', 'nhà hàng', 'quán ăn', 'đồ uống',
        }

        # Precomputed tokenized phrase list sorted by length desc for longest matching.
        self._phrase_tuples = sorted(
            [tuple(self.normalize_text(p).split()) for p in self.industry_phrases if p.strip()],
            key=len,
            reverse=True
        )

        # Query expansion dictionary (fallback by term).
        # IMPORTANT:
        # - Keep each list focused to avoid cross-domain noise.
        # - Use segmented tokens (e.g., điện_lực, dệt_may) when possible.
        # - Avoid mixing "electric power" with "electronics".
        self.query_expansions = {
            # Electric power utilities (điện năng / điện lực)
            'electric': ['điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện'],
            'electricity': ['điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện'],
            'power': ['điện_lực', 'điện_năng', 'phát_điện'],

            # Energy (do not force same intent as electricity utility)
            'energy': ['năng_lượng', 'năng_lượng_tái_tạo', 'điện_mặt_trời', 'điện_gió'],
            'renewable': ['năng_lượng_tái_tạo', 'điện_mặt_trời', 'điện_gió'],

            # Electronics / Electrical equipment (separate from electric utility)
            'electronics': ['điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử'],
            'electronic': ['điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử'],
            'electrical': ['thiết_bị_điện', 'cơ_điện', 'điện_công_nghiệp'],

            # Textile split into clearer sub-intents
            'textile': ['dệt_may', 'sợi_dệt', 'vải_dệt', 'nhuộm_vải'],
            'fabric': ['vải', 'vải_dệt', 'vải_không_dệt'],
            'garment': ['may_mặc', 'phụ_liệu_may_mặc', 'dệt_may'],
            'weaving': ['sợi_dệt', 'vải_dệt', 'dệt_may'],

            # Tech
            'technology': ['công_nghệ_thông_tin', 'phần_mềm', 'dữ_liệu_lớn'],
            'software': ['phần_mềm', 'công_nghệ_thông_tin'],
            # Vietnamese tech terms for direct local-language queries.
            'công_nghệ': ['công_nghệ_thông_tin', 'phần_mềm', 'dữ_liệu_lớn'],
            'công_nghệ_thông_tin': ['công_nghệ', 'phần_mềm', 'dữ_liệu_lớn'],
            'it': ['công_nghệ_thông_tin', 'phần_mềm'],

            # Healthcare
            'medical': ['y_tế', 'trang_thiết_bị_y_tế', 'phòng_khám', 'bệnh_viện'],
            'pharma': ['dược_phẩm', 'thuốc', 'y_tế'],

            # Other domains
            'construction': ['xây_dựng', 'vật_liệu_xây_dựng', 'công_trình'],
            'logistics': ['vận_tải', 'kho_bãi', 'logistics'],
            'finance': ['tài_chính', 'ngân_hàng', 'bảo_hiểm'],
            'bank': ['ngân_hàng', 'tài_chính'],
            'retail': ['bán_lẻ', 'cửa_hàng'],
            'food': ['thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống', 'nhà_hàng', 'quán_ăn', 'đồ_uống'],
            'restaurant': ['nhà_hàng', 'quán_ăn', 'dịch_vụ_ăn_uống'],
            'beverage': ['đồ_uống', 'ăn_uống'],
        }

        # Intent groups are used for higher precision expansion.
        # If query hits one group, only terms from that group are expanded.
        # This prevents accidental broadening across related-but-different sectors.
        self.intent_groups = {
            'electric_power': {
                'triggers': {'electric', 'electricity', 'power', 'điện_lực', 'điện_năng', 'phát_điện'},
                'expansions': ['điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện']
            },
            'energy': {
                'triggers': {'energy', 'renewable', 'năng_lượng', 'năng_lượng_tái_tạo', 'điện_gió', 'điện_mặt_trời'},
                'expansions': ['năng_lượng', 'năng_lượng_tái_tạo', 'điện_mặt_trời', 'điện_gió']
            },
            'electronics': {
                'triggers': {'electronics', 'electronic', 'electrical', 'điện_tử', 'thiết_bị_điện_tử', 'thiết_bị_điện'},
                'expansions': ['điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử', 'thiết_bị_điện', 'cơ_điện']
            },
            'home_appliance': {
                # Separate group for consumer electric home appliances.
                'triggers': {'gia_dụng', 'điện_gia_dụng', 'đồ_điện_gia_dụng', 'điện_lạnh', 'appliance', 'appliances'},
                'expansions': ['điện_gia_dụng', 'đồ_điện_gia_dụng', 'điện_lạnh', 'thiết_bị_điện']
            },
            'textile': {
                'triggers': {'textile', 'fabric', 'weaving', 'dệt_may', 'vải', 'nhuộm_vải', 'sợi_dệt'},
                'expansions': ['dệt_may', 'sợi_dệt', 'vải_dệt', 'vải_không_dệt', 'nhuộm_vải']
            },
            'garment': {
                'triggers': {'garment', 'may_mặc', 'phụ_liệu_may_mặc'},
                'expansions': ['may_mặc', 'phụ_liệu_may_mặc', 'dệt_may']
            },
            'technology': {
                # Dedicated technology intent to avoid mixing with generic "công" terms.
                'triggers': {'technology', 'software', 'it', 'công_nghệ', 'công_nghệ_thông_tin', 'phần_mềm'},
                'expansions': ['công_nghệ', 'công_nghệ_thông_tin', 'phần_mềm', 'dữ_liệu_lớn']
            },
            'food_service': {
                # Dedicated F&B intent to avoid matching generic words like "nhà", "hàng".
                'triggers': {'food', 'restaurant', 'beverage', 'thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống', 'nhà_hàng', 'quán_ăn', 'đồ_uống'},
                'expansions': ['thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống', 'nhà_hàng', 'quán_ăn', 'đồ_uống']
            },
        }

        # Intent disambiguation rules (column-aware).
        # Use these rules in ranker so intent in column A is not mixed with column B.
        # Example: electric_power should avoid docs whose business field is electronics/home-appliance.
        self.intent_column_rules = {
            'electric_power': {
                'positive': {'điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện'},
                'negative': {'điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử', 'điện_gia_dụng', 'đồ_điện_gia_dụng', 'điện_lạnh'}
            },
            'electronics': {
                'positive': {'điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử'},
                'negative': {'điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện'}
            },
            'home_appliance': {
                'positive': {'điện_gia_dụng', 'đồ_điện_gia_dụng', 'điện_lạnh', 'thiết_bị_điện'},
                'negative': {'điện_lực', 'điện_năng', 'phát_điện'}
            },
            'food_service': {
                'positive': {'thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống', 'nhà_hàng', 'quán_ăn', 'đồ_uống'},
                # Exclude medical/pharma-like business lines for pure food queries.
                'negative': {'dược_phẩm', 'thuốc', 'y_tế', 'mỹ_phẩm'}
            }
        }

        # Generic query words that should not become "intent terms".
        # Example: "company" appears almost everywhere and is not discriminative.
        self.generic_query_terms = {
            'company', 'companies', 'enterprise', 'business', 'corporation', 'corp', 'co', 'ltd',
            'industry', 'industries',
            'doanh', 'nghiệp', 'công', 'ty', 'cty', 'dn', 'ngành', 'nghề',
            # Generic location/store words that may create noise in strict intent.
            'nhà', 'hàng', 'cửa',
        }

    def normalize_text(self, text: str) -> str:
        """Normalize Vietnamese text"""
        if not text:
            return ""

        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # Normalize unicode in composed form to preserve Vietnamese characters.
        # NOTE:
        #   Using NFKD may split accented chars into base + combining marks,
        #   then regex cleaning can break words like "công_nghệ" into fragments.
        #   NFC keeps accents stable and avoids token corruption.
        text = unicodedata.normalize('NFC', text)

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

        # Apply phrase segmentation (longest matching first).
        # This is the core step to improve industry-level precision.
        tokens = self.segment_phrases(tokens)

        return tokens

    def segment_phrases(self, tokens: List[str]) -> List[str]:
        """
        Segment token list into phrase tokens using maximum/longest matching.

        Example:
            ["công", "nghiệp", "dệt", "may"] -> ["công", "nghiệp", "dệt_may"]
        """
        if not tokens or not self._phrase_tuples:
            return tokens

        segmented: List[str] = []
        i = 0

        while i < len(tokens):
            matched = False

            # Try longest phrase first, then shorter phrases.
            for phrase in self._phrase_tuples:
                phrase_len = len(phrase)
                if i + phrase_len > len(tokens):
                    continue

                if tuple(tokens[i:i + phrase_len]) == phrase:
                    segmented.append('_'.join(phrase))
                    i += phrase_len
                    matched = True
                    break

            if not matched:
                segmented.append(tokens[i])
                i += 1

        return segmented

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove stopwords from token list"""
        return [token for token in tokens if token not in self.stopwords and len(token) > 1]

    def process(self, text: str, remove_stops: bool = True) -> List[str]:
        """Full preprocessing pipeline"""
        tokens = self.tokenize(text)
        if remove_stops:
            tokens = self.remove_stopwords(tokens)
        return tokens

    def build_search_terms(self, query: str) -> tuple[List[str], List[str]]:
        """
        Build robust search terms for ranking.

        Returns:
            (expanded_terms, intent_terms)

        - expanded_terms: terms used to retrieve candidates (broader recall)
        - intent_terms: domain/core terms used for strict filtering (better precision)
        """
        base_terms = self.process(query, remove_stops=True)
        if not base_terms:
            return [], []

        def _expand_term(phrase_or_token: str) -> List[str]:
            """
            Expand a term/phrase safely through the same preprocessing pipeline.
            Underscore phrase tokens are converted back to spaces first so
            segmentation can decide whether to keep them as phrase tokens.
            """
            normalized = phrase_or_token.replace('_', ' ')
            return self.process(normalized, remove_stops=True)

        expanded_terms: List[str] = []
        intent_terms: List[str] = []

        # Detect which intent groups are activated by the query.
        # If any group matches, expansion is restricted to that group only.
        # This is the key improvement to reduce overlapping keyword noise.
        activated_groups = []
        base_set = set(base_terms)
        for group_name, group_data in self.intent_groups.items():
            if base_set.intersection(group_data['triggers']):
                activated_groups.append(group_name)

        for term in base_terms:
            expanded_terms.append(term)

            # If query is not in a specific group, fallback to per-term expansion.
            if not activated_groups and term in self.query_expansions:
                for expansion in self.query_expansions[term]:
                    expanded_terms.extend(_expand_term(expansion))

            # Identify intent terms (exclude generic words like company/công ty).
            if term not in self.generic_query_terms:
                intent_terms.append(term)

        # Group-aware expansion for precision.
        for group_name in activated_groups:
            for expansion in self.intent_groups[group_name]['expansions']:
                expanded_terms.extend(_expand_term(expansion))

        # Keep order but remove duplicates.
        expanded_terms = list(dict.fromkeys(expanded_terms))
        intent_terms = list(dict.fromkeys(intent_terms))

        # If expansion produced strong domain terms, add them into intent terms as well.
        # This is important for English queries over Vietnamese data.
        for term in expanded_terms:
            if term not in self.generic_query_terms and term not in intent_terms:
                # Keep intent list compact to avoid over-restricting.
                if len(intent_terms) < 8:
                    intent_terms.append(term)

        return expanded_terms, intent_terms

    def detect_intent_group(self, terms: List[str]) -> str | None:
        """
        Detect one dominant intent group from tokenized query terms.
        Priority order helps separate similar domains like electric power vs electronics.
        """
        if not terms:
            return None

        term_set = set(terms)
        priority = ['electric_power', 'electronics', 'home_appliance', 'technology', 'food_service', 'energy', 'textile', 'garment']

        for group_name in priority:
            group_data = self.intent_groups.get(group_name)
            if not group_data:
                continue
            if term_set.intersection(group_data['triggers']):
                return group_name

        return None


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
