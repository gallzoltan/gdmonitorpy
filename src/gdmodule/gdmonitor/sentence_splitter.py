"""Könnyűsúlyú magyar mondathatár-kereső.

A Magyar Közlöny szövege tele van olyan pontokkal, amelyek nem mondatvégek:
sorszámok („14.”), dátumok („2024. évi”), házszámok („Munkás u. 28.”),
jogszabályi hivatkozások („1386/2024. (XII. 9.) Korm. határozat”) és az
aláírás („Orbán Viktor s. k.,”). Egy naiv [.!?] szerinti vágás ezeket
mind mondathatárnak vinné, ezért a vágás két feltételhez kötött:

- a pont előtti szó nem szerepel a rövidítéslistán, és
- a pont nem számjegy után áll.

Ez a modul váltotta ki a korábbi huSpaCy pipeline-t, amely a 438 MB-os
hu_core_news_lg modellt csak azért töltötte be, hogy az összefoglalóhoz
kivegye az első néhány mondatot.
"""

import re

# Rövidítések, amelyek záró pontja nem mondatvég. Kisbetűsen hasonlítjuk.
ABBREVIATIONS = frozenset([
    "s", "k", "u", "sz", "ill", "pl", "stb", "korm", "hat", "vö", "ún",
    "kb", "kft", "zrt", "nyrt", "bt", "kkt", "krt", "dr", "prof", "ifj",
    "özv", "tkp", "ún", "évf", "fő", "min", "ún", "hrsz", "em", "ép",
])

# Mondathatár-jelölt: írásjel, opcionális záró idézőjel/zárójel, whitespace,
# majd nagybetű vagy nyitó idézőjel. A pont előtti szót külön kapjuk el,
# hogy a rövidítés- és számjegyvizsgálat elvégezhető legyen.
_BOUNDARY = re.compile(
    r"(?P<word>\w*)"
    r"(?P<punct>[.!?])"
    r"(?P<close>[”\"'’»)\]]?)"
    r"\s+"
    r"(?=[„«\"(\[]?[A-ZÁÉÍÓÖŐÚÜŰ])"
)


def _is_boundary(match):
    """Eldönti, hogy a jelölt valóban mondathatár-e."""
    if match.group("punct") != ".":
        return True

    word = match.group("word")
    if not word:
        return True
    if word[-1].isdigit():
        return False
    return word.lower() not in ABBREVIATIONS


def split_sentences(text, max_sentences=None, scan_limit=2000):
    """Mondatokra bontja a szöveget.

    Args:
        text: A feldolgozandó szöveg.
        max_sentences: Ha meg van adva, legfeljebb ennyi mondatot ad vissza.
        scan_limit: Csak a szöveg ekkora előtagját vizsgálja. A határozatok
            akár 32 000 karakteresek is lehetnek, az összefoglalóhoz viszont
            csak az elejük kell.

    Returns:
        A mondatok listája; üres bemenetre üres lista.
    """
    if not text:
        return []

    head = text[:scan_limit] if scan_limit else text

    sentences = []
    start = 0
    for match in _BOUNDARY.finditer(head):
        if not _is_boundary(match):
            continue
        end = match.end("close")
        sentence = head[start:end].strip()
        if sentence:
            sentences.append(sentence)
            if max_sentences and len(sentences) >= max_sentences:
                return sentences
        start = match.end()

    tail = head[start:].strip()
    if tail:
        sentences.append(tail)

    if max_sentences:
        return sentences[:max_sentences]
    return sentences
