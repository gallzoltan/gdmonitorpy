import os
import logging
import argparse
from fetcher import GazetteFetcher
from dotenv import load_dotenv


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
        print(f"{len(downloaded)} új Magyar Közlöny került letöltésre:")
        for filename in downloaded:
            print(f"- {filename}")
    else:
        print("Nem került letöltésre új Magyar Közlöny.")        

if __name__ == "__main__":
    main()