import datetime
from gdmonitor.resulation_analyzer import analyze_resolutions

def test_analyze_resolutions():
    """
    test_analyze_resolutions(): Ellenőrzi, hogy a függvény helyesen azonosítja-e a releváns határozatokat 
    a kulcsszavak alapján, megfelelően számolja-e a relevancia pontszámot, 
    és helyesen készíti-e el az összefoglalót.
    
    test_no_relevant_resolutions(): Teszteli, hogy helyesen működik-e a függvény, amikor a 
    bemeneti határozatok között egy sem tartalmaz releváns kulcsszavakat.
  
    test_empty_resolutions(): Ellenőrzi, hogy üres bemeneti lista esetén a függvény megfelelően üres eredményt ad-e vissza.
    """
    
    test_resolutions = [
        {
            'number': '1234',
            'year': '2024',
            'month': 5,
            'day': 15,
            'date': datetime.date(2024, 5, 15),
            'title': 'A Kormány 1234/2024. (V. 15.) Korm. határozata a helyi önkormányzat támogatásáról',
            'content': 'A Kormány dönt a helyi önkormányzat támogatásáról. Az iparűzési adó kiegészítésre kerül.'
        },
        {
            'number': '5678',
            'year': '2024',
            'month': 6,
            'day': 20,
            'date': datetime.date(2024, 6, 20),
            'title': 'A Kormány 5678/2024. (VI. 20.) Korm. határozata más témáról',
            'content': 'Ez a határozat nem tartalmaz önkormányzati vonatkozású szöveget.'
        },
        {
            'number': '9101',
            'year': '2024',
            'month': 7,
            'day': 25,
            'date': datetime.date(2024, 7, 25),
            'title': 'A Kormány 9101/2024. (VII. 25.) Korm. határozata',
            'content': 'Ebben a határozatban szerepel az önkormányzati adósság kezelésének kérdése.'
        }
    ]
    
    # Elemezzük a határozatokat
    results = analyze_resolutions(test_resolutions)
    
    # Ellenőrizzük az eredményeket
    assert results['total_resolutions'] == 3, "Összesen 3 határozatot adtunk meg"
    
    # Két határozatnak kell relevánsnak lennie
    assert len(results['relevant_resolutions']) == 2, "2 releváns határozatot kellett volna találni"
    
    # Első releváns határozat (a relevance_score alapján sorba rendezve)
    first_relevant = results['relevant_resolutions'][0]
    assert first_relevant['resolution']['number'] in ['1234', '9101'], "Az első releváns határozat száma nem megfelelő"
    assert first_relevant['relevance_score'] > 0, "A relevancia pontszám nagyobb kell legyen mint 0"
    assert len(first_relevant['keyword_matches']) > 0, "Legalább egy kulcsszónak kell egyeznie"
    assert first_relevant['summary'] != "", "Az összefoglalónak nem szabad üresnek lennie"
    
    # Ellenőrizzük, hogy a nem releváns határozat nincs a releváns határozatok között
    non_relevant_numbers = [r['resolution']['number'] for r in results['relevant_resolutions']]
    assert '5678' not in non_relevant_numbers, "A nem releváns határozatot is relevánsnak jelölte"

def test_no_relevant_resolutions():
    # Olyan határozatok, amikben nincs releváns kulcsszó
    test_resolutions = [
        {
            'number': '1234',
            'year': '2024',
            'month': 5,
            'day': 15,
            'date': datetime.date(2024, 5, 15),
            'title': 'A Kormány 1234/2024. (V. 15.) Korm. határozata egyéb témáról',
            'content': 'Ez a kormányhatározat nem tartalmaz önkormányzatokra vonatkozó információt.'
        }
    ]
    
    results = analyze_resolutions(test_resolutions)
    
    assert results['total_resolutions'] == 1, "Összesen 1 határozatot adtunk meg"
    assert len(results['relevant_resolutions']) == 0, "Nem kellene releváns határozatot találni"

def test_empty_resolutions():
    # Üres lista esetén
    results = analyze_resolutions([])
    
    assert results['total_resolutions'] == 0, "Üres listát adtunk meg"
    assert len(results['relevant_resolutions']) == 0, "Üres lista esetén nem lehet releváns határozat"