"""String matching utilities — normalize text and score string matches for entity resolution."""
import re


def normalize(text: str) -> str:
    """Strip punctuation separators, lowercase, collapse whitespace."""
    text = re.sub(r'[:\-_]', ' ', text)
    return " ".join(text.lower().strip().split())


def score(query: str, target: str) -> int:
    """
    Fuzzy match score between query and target strings using difflib. Returns 0–100.
    """
    from difflib import SequenceMatcher
    
    if query == target:          return 100
    if target.startswith(query): return 85
    if query in target:          return 70
    
    # Calculate fuzzy ratio
    ratio = int(SequenceMatcher(None, query, target).ratio() * 100)
    
    # Check word overlap as a secondary measure
    q = set(query.split()); t = set(target.split())
    ov = q & t
    overlap_score = 0
    if ov:
        overlap_score = 50 + int(30 * len(ov) / max(len(q), 1))
        
    return max(ratio, overlap_score)
