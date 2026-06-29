import re
import math

def tokenize_words(text: str) -> list[str]:
    """
    Cleans text, splits it into lowercase words, and strips punctuation.
    """
    words = re.findall(r"\b\w+\b", text.lower())
    return words

def get_sentences(text: str) -> list[str]:
    """
    Splits text into sentences based on punctuation boundary markers.
    """
    # Split on periods, exclamation marks, question marks followed by space or end of string
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    # Filter out empty strings
    return [s for s in sentences if s.strip()]

def calculate_ttr(words: list[str]) -> float:
    """
    Calculates Type-Token Ratio (vocabulary diversity).
    TTR = unique words / total words.
    """
    if not words:
        return 0.0
    return len(set(words)) / len(words)

def calculate_slv(sentences: list[str]) -> float:
    """
    Calculates the variance in sentence length (number of words per sentence).
    Returns the standard deviation (or 0.0 if not enough sentences).
    """
    if len(sentences) <= 1:
        return 0.0
        
    sentence_lengths = [len(tokenize_words(s)) for s in sentences]
    # Filter out zero-length sentences
    sentence_lengths = [l for l in sentence_lengths if l > 0]
    
    if len(sentence_lengths) <= 1:
        return 0.0
        
    mean = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((x - mean) ** 2 for x in sentence_lengths) / (len(sentence_lengths) - 1)
    
    return math.sqrt(variance)

def normalize_ttr(ttr: float) -> float:
    """
    Normalizes Type-Token Ratio to a 0.0 (likely human) - 1.0 (likely AI) scale.
    AI writing has lower vocabulary diversity (lower TTR).
    We define standard thresholds:
    - High human diversity: TTR >= 0.65 -> maps to score ~0.0
    - Mid diversity: TTR = 0.50 -> maps to score ~0.50
    - Low AI-like diversity: TTR <= 0.35 -> maps to score ~1.0
    We use a linear interpolation clamped between 0 and 1.
    """
    if ttr >= 0.65:
        return 0.0
    if ttr <= 0.35:
        return 1.0
    # Linear interpolation between 0.35 and 0.65, inverting so lower TTR -> higher score
    return (0.65 - ttr) / 0.30

def normalize_slv(slv: float) -> float:
    """
    Normalizes Sentence Length Variance to a 0.0 (likely human) - 1.0 (likely AI) scale.
    AI writing has very uniform sentence length (low standard deviation, e.g. SLV < 2.0).
    Human writing has high variance (high standard deviation, e.g. SLV > 6.0).
    We define standard thresholds:
    - High human variance: SLV >= 6.0 -> maps to score ~0.0
    - Low AI-like variance: SLV <= 2.0 -> maps to score ~1.0
    Linear interpolation between 2.0 and 6.0, inverting so lower SLV -> higher score.
    """
    if slv >= 6.0:
        return 0.0
    if slv <= 2.0:
        return 1.0
    # Linear interpolation between 2.0 and 6.0, inverting so lower SLV -> higher score
    return (6.0 - slv) / 4.0

def analyze_stylometrics(text: str) -> float:
    """
    Computes sentence variance and vocabulary diversity, normalizes them,
    and returns a combined stylometric score from 0.0 (human) to 1.0 (AI).
    """
    words = tokenize_words(text)
    sentences = get_sentences(text)
    
    # Handle extremely short text edge cases
    if len(words) < 20 or len(sentences) < 2:
        # Not enough text to build stylometrics: return neutral 0.5 score
        return 0.5
        
    ttr = calculate_ttr(words)
    slv = calculate_slv(sentences)
    
    ttr_score = normalize_ttr(ttr)
    slv_score = normalize_slv(slv)
    
    # Combine scores: equal weights for TTR and SLV
    style_score = 0.5 * ttr_score + 0.5 * slv_score
    return round(style_score, 2)
