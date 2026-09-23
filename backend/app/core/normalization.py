import re
from typing import Dict

# Exact word replacements for abbreviations (must match as full words)
ABBREVIATIONS: Dict[str, str] = {
    "BRG": "BEARING",
    "BRNG": "BEARING",
    "DIA": "DIAMETER",
    "SS": "STAINLESS STEEL",
    "CS": "CARBON STEEL",
    "GALV": "GALVANIZED",
    "ASSY": "ASSEMBLY",
    "MTR": "MOTOR",
    "VLV": "VALVE"
}

# Ambiguous abbreviations we intentionally do NOT expand blindly:
# "IN" (could be inch or in), "NO" (could be number or normally open), "ST" (could be street or steel)
# We handle engineering notations specifically.

class TextNormalizer:
    VERSION = "1.0.0"

    @classmethod
    def normalize_description(cls, raw_desc: str) -> str:
        if not raw_desc:
            return ""

        # 1. Case normalization
        desc = raw_desc.upper()

        # 2. Punctuation and symbols
        # Replace hyphens/underscores/commas with spaces to separate words, 
        # but keep decimal points and dimensions if they are part of a number (e.g. 1.5, 1/2)
        desc = re.sub(r'[_,;]+', ' ', desc)
        
        # Keep hyphens between letters/numbers but remove dangling ones? 
        # Actually, let's just make it simpler: standard spacing.
        
        # 3. Engineering notation:
        # Standardize inch notations: '' or " or IN. -> IN
        desc = re.sub(r'(?<=\d)\s*(?:"|\'\')', ' IN', desc)
        
        # Standardize mm
        desc = re.sub(r'(?<=\d)\s*MM\b', ' MM', desc)

        # 4. Whitespace: remove extra spaces
        desc = re.sub(r'\s+', ' ', desc).strip()

        # 5. Abbreviations and synonyms
        # Use regex word boundaries to prevent substring replacement (e.g. 'CROSS' shouldn't become 'CSTAINLESS STEEL' if SS matched substring)
        words = desc.split(' ')
        normalized_words = []
        for word in words:
            # Strip trailing periods from abbreviations like "DIA." -> "DIA"
            clean_word = word.rstrip('.')
            if clean_word in ABBREVIATIONS:
                normalized_words.append(ABBREVIATIONS[clean_word])
            else:
                normalized_words.append(word)

        desc = ' '.join(normalized_words)
        
        # Clean up any resulting double spaces
        desc = re.sub(r'\s+', ' ', desc).strip()
        
        return desc
