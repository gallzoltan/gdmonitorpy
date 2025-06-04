import os
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from fetcher import GazetteFetcher
from repository import GazetteRepository
from gdmonitor import extract_text_from_pdf, extract_resolutions, analyze_gdecision

logger = logging.getLogger(__name__)

def setup_logging():
    """Beállítja a naplózást"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def setup_fetcher():
    """Beállítja a Magyar Közlöny letöltő objektumot"""
    feed_url = os.getenv('FEED_URL')
    if not feed_url:
        raise ValueError("A FEED_URL környezeti változó nincs beállítva.")
    db_file = os.getenv('DB_FILE')
    if not db_file:
        raise ValueError("A DB_PATH környezeti változó nincs beállítva.")
    download_path = os.getenv('DOWNLOAD_PATH')
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    since_date = os.getenv('SINCE_DATE')  # YYYY-MM-DD formátum
    return GazetteFetcher(feed_url=feed_url, db_file=db_file, download_path=download_path, since_date=since_date)

def main():
    setup_logging()
    load_dotenv()
    parser = argparse.ArgumentParser(description='PDF kormányhatározat feldolgozó')
    parser.add_argument('--analyze', action='store_true', help='Önkormányzati tartalom elemzése')
    parser.add_argument('--email', action='store_true', help='Email küldése az eredményekről')
    parser.add_argument('--since', type=str, help='Csak ezen dátum után megjelent közlönyök (YYYY-MM-DD)')
    args = parser.parse_args()

    # Ha parancssori argumentumként megadták a dátumot, felülírja a környezeti változót
    if args.since:
        os.environ['SINCE_DATE'] = args.since

    fetcher = setup_fetcher()
    downloaded = fetcher.fetch_new_gazettes()
    if downloaded:
        logger.info(f"{len(downloaded)} új Magyar Közlöny került letöltésre:")
        for filename in downloaded:
            logger.info(f"Letöltött közlöny: {filename}")
    else: 
        logger.info("Nem került letöltésre új Magyar Közlöny.")
    
    if args.analyze:
        repository = GazetteRepository(fetcher.db_path)
        unanalyzed_gazettes = repository.get_unanalyzed_gazettes()
        if unanalyzed_gazettes:
            logger.info(f"{len(unanalyzed_gazettes)} közlöny még nem lett elemezve.")            
            for gazette in unanalyzed_gazettes:
                logger.info(f"Elemzés: {gazette['title']} ({gazette['publication_date']})")               
                pdf_text = extract_text_from_pdf(fetcher.base_dir / fetcher.download_path / gazette['filename'])
                if pdf_text:
                    gdecisions = extract_resolutions(pdf_text)
                    if not gdecisions:
                        logger.info(f"Nincs kormányhatározat a közlönyben: {gazette['title']}")
                        repository.mark_as_analyzed(gazette['id'], is_relevant=False)
                        continue
                    logger.info(f"Kormányhatározatok száma: {len(gdecisions)}")
                    for i, gdecision in enumerate(gdecisions, 1):
                        # logger.info(f"Kormhat {i}. {gdecision['title']}")
                        result = analyze_gdecision(gdecision)
                        if result:
                            logger.info(f"Releváns: {gdecision['title']} pontszám: {result['relevance_score']}")
                            repository.mark_as_analyzed(gazette['id'], is_relevant=True)
                            repository.save_summary(gazette['id'], result['relevance_score'], result['keyword_matches'], result['summary'])
                        else:
                            logger.info(f"Nem releváns: {gdecision['title']}")
                            repository.mark_as_analyzed(gazette['id'], is_relevant=False)                        
                else:
                    logger.error(f"Nem sikerült a PDF szöveg kinyerése: {gazette['filename']}")
                    repository.mark_as_analyzed(gazette['id'], is_relevant=False)
        else:
            logger.info("Minden közlöny elemezve van már.")


if __name__ == "__main__":
    main()