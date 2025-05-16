import re
import huspacy

# NLP modell betöltése
try:
    # nlp = spacy.load("hu_core_news_lg")    
    nlp = huspacy.load()
except:
    import sys
    print("Magyar nyelvi modell letöltése...")
    huspacy.download("hu_core_news_lg")
    # huspacy.cli.download("hu_core_news_lg")
    nlp = huspacy.load("hu_core_news_lg")

def analyze_resolutions(resolutions):
    """
    Kormányhatározatok elemzése önkormányzati vonatkozású tartalom szempontjából.
    A címben való előfordulás kétszeres súlyt kap
    """

    keywords = [
        "ix. helyi önkormányzatok",
        "települési önkormányzatok", 
        "önkormányzatok adósságot keletkeztető",
        "gazdasági társaságok adósságot keletkeztető",
        "helyi önkormányzat",
        "önkormányzati adósság",
        "önkormányzati hitelfelvétel",
        "adósságot keletkeztető ügyletek",
        "iparűzési adó"
    ]
    
    relevant_resolutions = []
    
    for resolution in resolutions:
        relevance_score = 0
        keyword_matches = []
        
        # Ellenőrizzük a címben és a tartalomban a kulcsszavakat
        for keyword in keywords:
            title_matches = len(re.findall(r'\b' + keyword + r'\w*\b', resolution['title'].lower()))
            content_matches = len(re.findall(r'\b' + keyword + r'\w*\b', resolution['content'].lower()))
            
            if title_matches > 0 or content_matches > 0:
                keyword_matches.append({
                    'keyword': keyword,
                    'title_count': title_matches,
                    'content_count': content_matches
                })
                relevance_score += (title_matches * 2) + content_matches
                
        if relevance_score > 0:
            doc = nlp(resolution['content'])
            
            # Egyszerű összefoglaló készítése: az első pár mondat
            summary = '. '.join([sent.text for sent in list(doc.sents)[:3]])
            
            relevant_resolutions.append({
                'resolution': resolution,
                'relevance_score': relevance_score,
                'keyword_matches': keyword_matches,
                'summary': summary
            })
    
    # Eredmények rendezése relevancia szerint
    relevant_resolutions.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return {
        'total_resolutions': len(resolutions),
        'relevant_resolutions': relevant_resolutions
    }