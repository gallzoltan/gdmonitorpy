import re
import datetime
import logging

logger = logging.getLogger(__name__)

def extract_resolutions(text):
    """
    Kormányhatározatok kinyerése a szövegből és strukturált adattá alakítása.
    Rugalmasabb regex minta a kormányhatározatok azonosítására 
    Több whitespace-t és sortörést is engedélyez, rugalmasabb formátumot elfogad
    """
    # Diagnosztika - ellenőrizzük, hogy található-e a 'A Kormány határozata' szövegrész    
    resolution_pattern = r"A\s+Kormány\s+(\d+)[\/\s]+(\d{4})[\.|\s]+[\(]+((?:I|V|X|L|C|D|M)+)[\.|\s]+(\d+)[\.|\s]+[\)]+\s+Korm[\.|\s]+határozata(.*?)(?=A\s+Kormány\s+\d+[\/\s]+\d{4}|$)"
    matches = list(re.finditer(resolution_pattern, text, re.DOTALL | re.IGNORECASE))
    
    # logger.debug(f"Találatok száma 'A Kormány határozata' mintával: {len(matches)}")
    
    # Ha nincs találat, próbáljunk egy egyszerűbb mintát
    # if len(matches) == 0:
        # Nagyon egyszerű minta csak a címsor alapszerkezetével
        # simple_pattern = r"Korm[á|a]ny\s+(\d+)[\/|\s]+(\d{4})[\.|\s]+((?:I|V|X|L|C|D|M)+)[\.|\s]+(\d+)[\.|\s]+Korm[\.|\s]+hat[á|a]rozata"
        # simple_matches = list(re.finditer(simple_pattern, text, re.DOTALL | re.IGNORECASE))
        # logger.info(f"Egyszerűbb mintával találatok száma: {len(simple_matches)}")        
        # Mutassunk egy mintát a szövegből, ahol esetleg kormányhatározat lehet
        # sample_text = text.find("Kormány")
        # if sample_text != -1:
        #     print("Minta a szövegből, ahol a 'Kormány' szó található:")
        #     print(text[sample_text:sample_text+150])
    
    resolutions = []
    for match in matches:
        try:
            number = match.group(1)
            year = match.group(2)
            month_roman = match.group(3)
            day = match.group(4)
            content = match.group(5).strip() if match.group(5) else ""
            
            # Római szám konvertálása decimálissá
            month_mapping = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12}
            month = month_mapping.get(month_roman.upper(), 0)
            
            title = f"A Kormány {number}/{year}. ({month_roman}. {day}.) Korm. határozata"
            
            resolution = {
                'number': number,
                'year': year,
                'month': month,
                'day': int(day),
                'date': datetime.date(int(year), month, int(day)),
                'title': title,
                'content': content
            }
            
            resolutions.append(resolution)
        except Exception as e:
            print(f"Hiba a feldolgozás közben: {e}")
    
    return resolutions