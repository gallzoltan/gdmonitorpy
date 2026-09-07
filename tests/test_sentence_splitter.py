from gdmodule.gdmonitor.sentence_splitter import split_sentences


def test_splits_on_real_sentence_end():
    text = "A Kormány dönt az aláírásáról. Felelős: miniszter Határidő: azonnal"
    assert split_sentences(text) == [
        "A Kormány dönt az aláírásáról.",
        "Felelős: miniszter Határidő: azonnal",
    ]


def test_does_not_split_on_signature_abbreviation():
    """Az "s. k." aláírás nem mondathatár."""
    text = "A megállapodás megkötéséről. Orbán Viktor s. k., miniszterelnök"
    assert split_sentences(text) == [
        "A megállapodás megkötéséről.",
        "Orbán Viktor s. k., miniszterelnök",
    ]


def test_does_not_split_on_house_number():
    """A "Munkás u. 28.;" házszám nem mondathatár."""
    text = "A Társaság (székhely: 8660 Tab, Munkás u. 28.; cégjegyzékszám: 14-09-300339) között."
    assert len(split_sentences(text)) == 1


def test_does_not_split_on_legal_reference():
    """A "1386/2024. (XII. 9.) Korm. határozat" hivatkozás nem mondathatár."""
    text = "A szóló 1386/2024. (XII. 9.) Korm. határozat a következő ponttal egészül ki."
    assert len(split_sentences(text)) == 1


def test_does_not_split_on_list_ordinal():
    """A számozott listaelem ("„14. EUROPEAN") nem mondathatár."""
    text = 'ki: „14. EUROPEAN PERSONNEL RECOVERY CENTER kiképzés; 15. DEFENDER EUROPE gyakorlat.”'
    assert len(split_sentences(text)) == 1


def test_max_sentences_limits_output():
    text = "Egy mondat. Másik mondat. Harmadik mondat. Negyedik mondat."
    assert len(split_sentences(text, max_sentences=3)) == 3


def test_scan_limit_only_reads_the_head():
    """A vágó csak az előtagot nézi, nem a 32 000 karakteres teljes szöveget."""
    text = "Első mondat. " + ("Töltelék szöveg. " * 200) + "Utolsó mondat."
    result = split_sentences(text, scan_limit=200)

    assert result[0] == "Első mondat."
    assert "Utolsó mondat." not in result


def test_empty_input():
    assert split_sentences("") == []
    assert split_sentences(None) == []
