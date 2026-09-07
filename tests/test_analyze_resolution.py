import datetime

from gdmodule.gdmonitor.resulation_analyzer import analyze_gdecision


def _gdecision(title, content, number="1234"):
    return {
        'number': number,
        'year': '2024',
        'month': 5,
        'day': 15,
        'date': datetime.date(2024, 5, 15),
        'title': title,
        'content': content,
    }


def test_relevant_gdecision():
    """A kulcsszót tartalmazó határozat releváns, és összefoglalót kap."""
    result = analyze_gdecision(_gdecision(
        'A Kormány 1234/2024. (V. 15.) Korm. határozata a helyi önkormányzat támogatásáról',
        'A Kormány dönt a helyi önkormányzat támogatásáról. Az iparűzési adó kiegészítésre kerül.'
    ))

    assert result is not None
    assert result['relevance_score'] > 0
    assert 'helyi önkormányzat' in result['keyword_matches']
    assert result['summary'] != ""


def test_title_match_counts_double():
    """A címbeli előfordulás kétszeres súlyt kap a tartalombelihez képest."""
    in_title = analyze_gdecision(_gdecision(
        'A Kormány határozata a helyi önkormányzat ügyében',
        'Egyéb tartalom.'
    ))
    in_content = analyze_gdecision(_gdecision(
        'A Kormány határozata',
        'Szó esik a helyi önkormányzat ügyéről.'
    ))

    assert in_title['relevance_score'] == 2 * in_content['relevance_score']


def test_not_relevant_gdecision():
    """Kulcsszó nélkül nincs találat."""
    assert analyze_gdecision(_gdecision(
        'A Kormány 1234/2024. (V. 15.) Korm. határozata egyéb témáról',
        'Ez a kormányhatározat nem tartalmaz önkormányzatokra vonatkozó információt.'
    )) is None


def test_keyword_dot_is_escaped():
    """A kulcsszavak pontja nem joker: az "ix." nem illeszkedhet "ixa"-ra."""
    assert analyze_gdecision(_gdecision(
        'A Kormány határozata',
        'Az ixa helyi önkormányzatok kérdése nem ez a kulcsszó.'
    ))['keyword_matches'] == 'helyi önkormányzat'
