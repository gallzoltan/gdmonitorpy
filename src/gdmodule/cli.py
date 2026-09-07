"""Parancssori belépési pont a Magyar Közlöny figyeléséhez."""

import argparse
import logging
import os
import sys

from dotenv import find_dotenv, load_dotenv

from gdmodule.fetcher import GazetteFetcher
from gdmodule.gdmonitor import (
    analyze_gdecision,
    extract_resolutions,
    extract_text_from_pdf,
)
from gdmodule.repository import GazetteRepository
from gdmodule.sender import EmailSender

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2


class ConfigError(Exception):
    """Hiányzó vagy hibás konfiguráció."""


def setup_logging():
    """Beállítja a naplózást. A szintet a LOG_LEVEL környezeti változó adja."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        level = logging.INFO

    # A naplósorok magyar ékezeteket tartalmaznak. Konténerben a LANG=C.UTF-8
    # elég hozzá, fejlesztői Windows konzolon (cp1252) viszont a logolás
    # UnicodeEncodeError-ra futna, ezért itt kényszerítjük az UTF-8-at.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


def require_env(*names):
    """Ellenőrzi, hogy a felsorolt környezeti változók mind be vannak-e állítva.

    Egyszerre panaszkodik az összes hiányzóra, hogy egy futásból kiderüljön,
    mi hiányzik a konfigurációból.
    """
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise ConfigError(
            "Hiányzó környezeti változók: " + ", ".join(missing)
        )
    return [os.getenv(name) for name in names]


def setup_fetcher():
    """Beállítja a Magyar Közlöny letöltő objektumot."""
    feed_url, db_path, download_path = require_env(
        "FEED_URL", "DB_PATH", "DOWNLOAD_PATH"
    )

    # A SINCE_DATE statikus alsó korlát, nem állapot: soha nem írjuk vissza.
    # Az inkrementális működést az adatbázis URL-alapú deduplikációja adja.
    since_date = os.getenv("SINCE_DATE")

    return GazetteFetcher(
        feed_url=feed_url,
        db_path=db_path,
        download_path=download_path,
        certificate_path=os.getenv("CERTIFICATE_PATH"),
        since_date=since_date,
    )


def fetch(fetcher):
    """Új közlönyök letöltése."""
    downloaded = fetcher.fetch_new_gazettes()
    if downloaded:
        logger.info("%d új Magyar Közlöny került letöltésre:", len(downloaded))
        for filename in downloaded:
            logger.info("Letöltött közlöny: %s", filename)
    else:
        logger.info("Nem került letöltésre új Magyar Közlöny.")
    return downloaded


def analyze(fetcher):
    """A még nem elemzett közlönyök feldolgozása."""
    repository = GazetteRepository(fetcher.db_path)
    unanalyzed = repository.get_unanalyzed_gazettes()

    if not unanalyzed:
        logger.info("Minden közlöny elemezve van már.")
        return

    logger.info("%d közlöny még nem lett elemezve.", len(unanalyzed))

    for gazette in unanalyzed:
        logger.info(
            "Elemzés: %s (%s)", gazette["title"], gazette["publication_date"]
        )

        pdf_path = fetcher.download_path / gazette["filename"]
        pdf_text = extract_text_from_pdf(pdf_path)
        if not pdf_text:
            logger.error(
                "Nem sikerült a PDF szöveg kinyerése: %s", gazette["filename"]
            )
            repository.mark_as_analyzed(gazette["id"], is_relevant=False)
            continue

        gdecisions = extract_resolutions(pdf_text)
        if not gdecisions:
            logger.info("Nincs kormányhatározat a közlönyben: %s", gazette["title"])
            repository.mark_as_analyzed(gazette["id"], is_relevant=False)
            continue

        is_relevant = False
        for gdecision in gdecisions:
            result = analyze_gdecision(gdecision)
            if not result:
                logger.debug("Nem releváns: %s", gdecision["title"])
                continue

            is_relevant = True
            logger.info(
                "Releváns: %s pontszám: %s",
                gdecision["title"],
                result["relevance_score"],
            )
            repository.save_summary(
                gazette["id"],
                gdecision["title"],
                result["relevance_score"],
                result["keyword_matches"],
                result["summary"],
            )

        # A közlönyt egyszer, a határozatok feldolgozása után jelöljük meg.
        repository.mark_as_analyzed(gazette["id"], is_relevant=is_relevant)


def send_email(fetcher):
    """Digest küldése a releváns, még el nem küldött közlönyökről."""
    msg_server, msg_port = require_env("MSG_SERVER", "MSG_PORT")

    try:
        port = int(msg_port)
    except ValueError:
        raise ConfigError(f"A MSG_PORT értéke nem szám: {msg_port}")

    recipients = _recipients("EMAIL_TO")
    if not recipients:
        raise ConfigError("Az EMAIL_TO nincs beállítva.")

    sender = EmailSender(
        msg_server=msg_server, msg_port=port, db_path=fetcher.db_path
    )
    return sender.send_email(
        to_recipients=recipients,
        cc_recipients=_recipients("EMAIL_CC"),
        bcc_recipients=_recipients("EMAIL_BCC"),
    )


def _recipients(name):
    """Vesszővel elválasztott címlista beolvasása, üres elemek nélkül."""
    return [
        address.strip()
        for address in os.getenv(name, "").split(",")
        if address.strip()
    ]


def main():
    # Fejlesztői kényelem: ha a munkakönyvtárból felfelé található .env, azt
    # betöltjük. Konténerben nincs ilyen fájl, a konfiguráció környezeti
    # változókból jön — és soha nem írunk vissza egyikbe sem.
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file)

    setup_logging()

    parser = argparse.ArgumentParser(description="Magyar Közlöny figyelő")
    parser.add_argument(
        "--analyze", action="store_true", help="Önkormányzati tartalom elemzése"
    )
    parser.add_argument(
        "--email", action="store_true", help="Email küldése az eredményekről"
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Csak ezen dátum után megjelent közlönyök (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    if args.since:
        os.environ["SINCE_DATE"] = args.since

    try:
        fetcher = setup_fetcher()
        fetch(fetcher)

        if args.analyze:
            analyze(fetcher)

        if args.email:
            send_email(fetcher)
    except ConfigError as e:
        logger.error("Konfigurációs hiba: %s", e)
        return EXIT_CONFIG
    except Exception:
        logger.exception("A futás váratlan hibával leállt.")
        return EXIT_ERROR

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
