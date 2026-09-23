import re
import difflib

def tokenize_and_normalize(text: str) -> set:
    if not text:
        return set()
    text = str(text).lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = [t for t in text.split() if t.strip()]
    return set(tokens)

def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return len(intersection) / len(union)

def string_similarity(str_a: str, str_b: str) -> float:
    if not str_a and not str_b:
        return 1.0
    str_a = str(str_a).lower().strip()
    str_b = str(str_b).lower().strip()
    return difflib.SequenceMatcher(None, str_a, str_b).ratio()

class BaselineMatcher:
    def __init__(self, match_threshold=0.8):
        self.match_threshold = match_threshold

    def predict(self, str_a: str, str_b: str) -> dict:
        tokens_a = tokenize_and_normalize(str_a)
        tokens_b = tokenize_and_normalize(str_b)
        
        jaccard = jaccard_similarity(tokens_a, tokens_b)
        sequence = string_similarity(str_a, str_b)
        
        # Simple heuristic: heavily weight jaccard for unordered sets, fallback to string similarity
        combined_score = (jaccard * 0.7) + (sequence * 0.3)
        
        is_match = combined_score >= self.match_threshold
        
        return {
            'is_match': is_match,
            'score': combined_score,
            'jaccard': jaccard,
            'sequence_ratio': sequence
        }
