"""Kormányhatározatok elemzése önkormányzati vonatkozású tartalom szempontjából."""

import re
import logging

from .sentence_splitter import split_sentences

logger = logging.getLogger(__name__)

# A címben való előfordulás kétszeres súlyt kap.
KEYWORDS = [
    "ix. helyi önkormányzatok",
    "települési önkormányzatok",
    "önkormányzatok adósságot keletkeztető",
    "gazdasági társaságok adósságot keletkeztető",
    "helyi önkormányzat",
    "önkormányzati adósság",
    "önkormányzati hitelfelvétel",
    "adósságot keletkeztető ügyletek",
    "iparűzési adó",
]

# A kulcsszavakat escape-elni kell: a "ix. helyi önkormányzatok" pontja
# escape nélkül bármilyen karakterre illeszkedne.
_KEYWORD_PATTERNS = [
    (keyword, re.compile(r"\b" + re.escape(keyword) + r"\w*\b"))
    for keyword in KEYWORDS
]

# Az összefoglalóba ennyi mondat kerül.
SUMMARY_SENTENCES = 3


def analyze_gdecision(gdecision):
    """Egy kormányhatározat relevanciájának vizsgálata.

    Args:
        gdecision: Az extract_resolutions() által előállított szótár.

    Returns:
        A találat adatai, vagy None, ha a határozat nem releváns.
    """
    title = gdecision["title"].lower()
    content = gdecision["content"].lower()

    relevance_score = 0
    keyword_matches = []

    for keyword, pattern in _KEYWORD_PATTERNS:
        title_matches = len(pattern.findall(title))
        content_matches = len(pattern.findall(content))

        if title_matches or content_matches:
            keyword_matches.append(keyword)
            relevance_score += (title_matches * 2) + content_matches

    if not relevance_score:
        return None

    sentences = split_sentences(
        gdecision["content"], max_sentences=SUMMARY_SENTENCES
    )

    return {
        "gdecision": gdecision,
        "relevance_score": relevance_score,
        "keyword_matches": ", ".join(keyword_matches),
        "summary": " ".join(sentences),
    }
