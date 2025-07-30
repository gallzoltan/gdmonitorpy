import os
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from gdmodule.fetcher import GazetteFetcher
from gdmodule.repository import GazetteRepository
from gdmodule.gdmonitor import (
    extract_text_from_pdf,
    extract_resolutions,
    analyze_gdecision
)
from gdmodule.sender import EmailSender

logger = logging.getLogger(__name__)

def setup_logging():
    """Beállítja a naplózást"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def update_env_file(key, value):
    """Frissíti az .env fájlt egy kulcs-érték párral"""
    env_path = Path(__file__).parent / '.env'
    
    # Beolvassa a meglévő tartalmat
    lines = []
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Megkeresi és frissíti a kulcsot, vagy hozzáadja ha nem létezik
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
    
    # Ha nem találta meg, hozzáadja a végére
    if not updated:
        lines.append(f"{key}={value}\n")
    
    # Visszaírja a fájlt
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def setup_fetcher():
    """Beállítja a Magyar Közlöny letöltő objektumot"""
    feed_url = os.getenv('FEED_URL')
    if not feed_url:
        raise ValueError("A FEED_URL környezeti változó nincs beállítva.")
    db_path = os.getenv('DB_PATH')
    if not db_path:
        raise ValueError("A DB_PATH környezeti változó nincs beállítva.")
    download_path = os.getenv('DOWNLOAD_PATH')
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    since_date = os.getenv('SINCE_DATE')  # YYYY-MM-DD formátum
    return GazetteFetcher(feed_url=feed_url, db_path=db_path, download_path=download_path, since_date=since_date)

def main():
    setup_logging()
    
    # .env fájl betöltése a megfelelő útvonalról
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    
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
        # Frissítjük a SINCE_DATE értéket az .env fájlban is
        new_date = datetime.now().strftime("%Y-%m-%d")
        update_env_file('SINCE_DATE', new_date)
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
                    # logger.info(f"Kormányhatározatok száma: {len(gdecisions)}")
                    for i, gdecision in enumerate(gdecisions, 1):
                        result = analyze_gdecision(gdecision)
                        if result:
                            logger.info(f"Releváns: {gdecision['title']} pontszám: {result['relevance_score']}")                            
                            repository.save_summary(gazette['id'], gdecision['title'], result['relevance_score'], result['keyword_matches'], result['summary'])
                            repository.mark_as_analyzed(gazette['id'], is_relevant=True)
                        else:
                            logger.info(f"Nem releváns: {gdecision['title']}")
                            repository.mark_as_analyzed(gazette['id'], is_relevant=False)                                                                       
                else:
                    logger.error(f"Nem sikerült a PDF szöveg kinyerése: {gazette['filename']}")
                    repository.mark_as_analyzed(gazette['id'], is_relevant=False)
        else:
            logger.info("Minden közlöny elemezve van már.")
    
    if args.email:
        # Email küldés logika itt
        msg_server = os.getenv('MSG_SERVER')
        msg_port = int(os.getenv('MSG_PORT', 8025))  # Alapértelmezett port 8025
        db_path = Path(os.getenv('DB_PATH', 'gazettes.db'))
        email_sender = EmailSender(msg_server=msg_server, msg_port=msg_port, db_path=db_path)
        
        # Email címek tisztítása - üres stringek eltávolítása
        to_recipients = [email.strip() for email in os.getenv('EMAIL_TO', '').split(',') if email.strip()]
        cc_recipients = [email.strip() for email in os.getenv('EMAIL_CC', '').split(',') if email.strip()]
        bcc_recipients = [email.strip() for email in os.getenv('EMAIL_BCC', '').split(',') if email.strip()]
    
        email_sender.send_email(
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients   
        )


if __name__ == "__main__":
    main()