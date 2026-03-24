"""
src/research/sentiment.py

Sentiment scoring for news headlines.

Priority order
--------------
1. FinBERT (transformers) — finance-domain BERT, best accuracy.
2. TextBlob               — lightweight fallback if transformers not installed.

Usage
-----
    from src.research.sentiment import sentiment_from_news
    score = sentiment_from_news(["Reliance posts record profit", "HDFC cuts rates"])
    # returns float in [-1, +1]
"""

import logging

logger = logging.getLogger(__name__)

# Try FinBERT first
try:
    from transformers import pipeline as hf_pipeline
    _finbert = hf_pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        tokenizer="ProsusAI/finbert",
        truncation=True,
        max_length=512,
    )
    _BACKEND = "finbert"
    logger.info("Sentiment backend: FinBERT")
except Exception:
    _finbert  = None
    _BACKEND  = "textblob"
    logger.info("Sentiment backend: TextBlob (install transformers for FinBERT)")


def analyze_sentiment(text: str) -> float:
    """Returns sentiment polarity in [-1, +1]."""
    if _BACKEND == "finbert" and _finbert is not None:
        result = _finbert(text[:512])[0]
        label  = result["label"].lower()
        score  = result["score"]
        if label == "positive":
            return score
        elif label == "negative":
            return -score
        else:
            return 0.0
    else:
        from textblob import TextBlob
        return TextBlob(text).sentiment.polarity


def sentiment_from_news(news_list: list[str]) -> float:
    """Average sentiment across a list of headlines. Returns 0 if empty."""
    if not news_list:
        return 0.0
    scores = [analyze_sentiment(h) for h in news_list if h]
    return float(sum(scores) / len(scores)) if scores else 0.0


def sentiment_signal(row: dict) -> int:
    """
    Combine price momentum with news sentiment to produce a signal.

    Parameters
    ----------
    row : dict with keys 'returns' (float) and 'sentiment_score' (float)

    Returns
    -------
    +1 (buy), -1 (sell), or 0 (hold)
    """
    ret   = row.get("returns", 0)
    score = row.get("sentiment_score", 0)

    if ret > 0 and score > 0.15:
        return 1
    elif ret < 0 and score < -0.15:
        return -1
    return 0