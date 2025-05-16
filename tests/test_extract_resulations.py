import datetime
from gdmonitor.resulation_extractor import extract_resolutions

def test_extract_resolutions():
    ''' 
    test_extract_resolutions(): Ellenőrzi, hogy a szabályos kormányhatározatokat megfelelően kinyeri-e a függvény, 
    és helyesen felismeri-e a különböző mezőket (szám, dátum, stb.)
    
    test_empty_text(): Teszteli, hogy üres szöveg esetén helyesen működik-e a függvény
    
    test_no_resolutions(): Ellenőrzi, hogy olyan szöveg esetén, amelyben nincs kormányhatározat, 
    a függvény megfelelően üres listát ad-e vissza
    '''

    test_text = """
    A Kormány 1234/2024. (V. 15.) Korm. határozata
    a teszt kormányhatározat tartalmáról
    
    1. A Kormány támogatja a tesztprojekt megvalósítását.
    2. A Kormány felhívja a pénzügyminisztert, hogy gondoskodjon a szükséges forrásokról.
    
    A Kormány 5678/2024. (VI. 20.) Korm. határozata
    egy másik teszt határozatról
    
    1. A Kormány további intézkedésekről dönt.
    """
    
    # Hívjuk meg a tesztelendő függvényt
    results = extract_resolutions(test_text)
    
    # Ellenőrizzük az eredményeket
    assert len(results) == 2, "Két kormányhatározatot kellett volna találni"
    
    # Első határozat ellenőrzése
    first_resolution = results[0]
    assert first_resolution['number'] == '1234'
    assert first_resolution['year'] == '2024'
    assert first_resolution['month'] == 5
    assert first_resolution['day'] == 15
    assert first_resolution['date'] == datetime.date(2024, 5, 15)
    assert "teszt kormányhatározat" in first_resolution['content']
    
    # Második határozat ellenőrzése
    second_resolution = results[1]
    assert second_resolution['number'] == '5678'
    assert second_resolution['year'] == '2024'
    assert second_resolution['month'] == 6
    assert second_resolution['day'] == 20
    assert second_resolution['date'] == datetime.date(2024, 6, 20)
    assert "másik teszt határozatról" in second_resolution['content']
    
def test_empty_text():
    # Üres szöveg esetén
    results = extract_resolutions("")
    assert len(results) == 0, "Üres szöveg esetén nem szabad találatokat visszaadni"
    
def test_no_resolutions():
    # Olyan szöveg, amiben nincs határozat
    text_without_resolutions = "Ez a szöveg nem tartalmaz kormányhatározatot."
    results = extract_resolutions(text_without_resolutions)
    assert len(results) == 0, "Nem határozatot tartalmazó szöveg esetén nem szabad találatokat visszaadni"