"""PDF szövegkinyerés."""

import logging
import re

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path):
    """Kivonatolja a szöveget egy PDF fájlból.

    Args:
        pdf_path: A PDF fájl elérési útja.

    Returns:
        A PDF szövege egy sorba fűzve, hiba esetén üres string.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            parts = []
            page_count = 0
            for page in pdf.pages:
                page_count += 1
                # A pdfplumber None-t ad vissza a szöveg nélküli (például
                # szkennelt) oldalakra. Enélkül az összefűzés TypeError-t
                # dobna, és a tág except miatt az egész közlöny elveszne.
                parts.append(page.extract_text() or "")
            logger.debug(
                "%s - %d oldal: %d karakter",
                pdf_path,
                page_count,
                sum(len(part) for part in parts),
            )

        # Némi tisztítás a szövegen, töröljük a túl sok whitespace-t.
        return re.sub(r"\s+", " ", "\n".join(parts))
    except Exception as e:
        logger.error("Hiba a PDF feldolgozása során (%s): %s", pdf_path, e)
        return ""
