from gdmonitor.pdf_processor import extract_text_from_pdf

def test_extract_text_from_pdf(tmp_path):
    # Készítsünk egy egyszerű PDF-et teszteléshez
    test_pdf_path = tmp_path / "test.pdf"
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Ez egy Korm. határozat minta.", ln=True)
    pdf.output(str(test_pdf_path))

    # Teszteljük a függvényt
    text = extract_text_from_pdf(str(test_pdf_path))
    assert "Korm. határozat" in text