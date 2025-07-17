import pdfplumber
import logging
import re

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Kivonatolja a szöveget egy PDF fájlból.
    Args:
        pdf_path (str): A PDF fájl elérési útja.
    """
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for i, page in enumerate(pdf.pages):
                text += page.extract_text() + '\n' or ''
            logger.debug(f" - {i+1} oldal: {len(text) if text else 0} karakter")

        # Némi tisztítás a szövegen, töröljük a túl sok whitespace-t
        text = re.sub(r'\s+', ' ', text)
        return text
    except Exception as e:
        print(f"Hiba a PDF feldolgozása során: {e}")
        return ""