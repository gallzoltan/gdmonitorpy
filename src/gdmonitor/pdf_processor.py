import pdfplumber
import re

def extract_text_from_pdf(pdf_path):
    """
    Szöveg kinyerése a PDF fájlból.
    """
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # print(f"PDF oldalak száma: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                # print(f"  - {i+1}. oldal: {len(text) if text else 0} karakter")
        
        # Némi tisztítás a szövegen
        # Töröljük a túl sok whitespace-t
        full_text = re.sub(r'\s+', ' ', full_text)
        # Keressünk kormányhatározatot jelző szöveget
        korm_matches = re.findall(r'Korm[\.|\s]+hat[á|a]rozat', full_text)
        print(f"'Korm. határozat' típusú kifejezések száma: {len(korm_matches)}")
        
        return full_text
    except Exception as e:
        print(f"Hiba a PDF feldolgozása közben: {e}")
        return ""