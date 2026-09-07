import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests

from gdmodule.repository import GazetteRepository

logger = logging.getLogger(__name__)

# A relay REST hívásának időkorlátja másodpercben. Ütemezett batch job,
# timeout nélkül egy néma relay végtelenig lógatná a futást.
REQUEST_TIMEOUT = 30


class EmailSender:
    """Email küldő osztály a Magyar Közlöny elemzésekhez"""
    DB_PATH = "gazettes.db"

    def __init__(self, msg_server: str, msg_port: int, base_dir: str = None, db_path: Path = None):
        """
        Inicializálja az EmailSender objektumot
        """
        self.msg_server = msg_server
        self.msg_port = msg_port
        self.db_path = db_path if db_path else Path(self.DB_PATH)

        # Alapértelmezett könyvtár beállítása
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.cwd()
        self.db_path = self.base_dir / self.db_path
        self.repository = GazetteRepository(self.db_path)

    def send_email(self, to_recipients: List[str], cc_recipients: List[str] = None,
                   bcc_recipients: List[str] = None) -> bool:
        """Email küldése a megadott címre.

        Returns:
            True, ha a relay átvette a küldeményt, egyébként False.
        """

        if not self._validate_recipients(to_recipients):
            return False

        body, gazette_ids = self.create_content()
        if not body:
            logger.warning("Nincs tartalom az email küldéséhez.")
            return False

        url = f"http://{self.msg_server}:{self.msg_port}/api/v1/msg"
        headers = {
            "Content-Type": "application/json"
        }
        subject = "IX. Fejezettel kapcsolatos kormányhatározatok"
        dateSent = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "subject": subject,
            "body": body,
            "recipients": to_recipients if to_recipients else [],
            "ccRecipients": cc_recipients if cc_recipients else [],
            "bccRecipients": bcc_recipients if bcc_recipients else [],
            "dateSent": dateSent
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload),
                                     timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.error("Hiba az email küldése közben: %s", e)
            return False

        if response.status_code != 200:
            logger.error("Sikertelen email küldés. Státuszkód: %d", response.status_code)
            logger.error("Válasz: %s", response.text)
            return False

        logger.info("Az email sikeresen elküldve.")
        self.repository.mark_all_sent_email(gazette_ids)
        logger.info("%d közlöny megjelölve elküldöttként.", len(gazette_ids))

        if response.text.strip():
            try:
                logger.info("JSON válasz: %s", response.json())
            except json.JSONDecodeError:
                logger.warning("A válasz nem érvényes JSON: %s", response.text)
        else:
            logger.debug("Üres válasz érkezett a relay-től.")

        return True

    def create_content(self) -> Tuple[Optional[str], List[int]]:
        """Email tartalom létrehozása a közlöny adatokból.

        Returns:
            (HTML tartalom, közlöny azonosítók) pár. Ha nincs küldeni való,
            a tartalom None.
        """
        gazettes = self.repository.get_gazettes_for_email()

        if not gazettes:
            return None, []

        gazette_ids = []
        content = "<h2>IX. Fejezettel kapcsolatos kormányhatározatok</h2>\n"

        for gazette in gazettes:
            gazette_ids.append(gazette['id'])
            content += f"<h3>{gazette['title']}</h3>\n"
            content += f"<p><strong>Megjelenés dátuma:</strong> {gazette['publication_date']}</p>\n"
            content += f"<p><strong>URL:</strong> <a href=\"{gazette['url']}\">{gazette['url']}</a></p>\n"
            content += f"<p><strong>Kormányhatározat száma:</strong> {gazette['gdecision_title']}</p>\n"
            content += f"<p><strong>Relevancia pontszám:</strong> {gazette['relevant_score']}</p>\n"
            content += f"<p><strong>Kulcsszó egyezések:</strong> {gazette['keyword_matches']}</p>\n"
            content += f"<p><strong>Összefoglaló:</strong></p>\n"
            content += f"<p>{gazette['summary']}</p>\n"
            content += "<hr>\n\n"
        return content, gazette_ids

    def _validate_recipients(self, recipients: List[str]) -> bool:
        """Email címek validálása"""
        if not recipients:
            logger.error("Nincs megadva TO címzett")
            return False

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        for email in recipients:
            if not re.match(email_pattern, email):
                logger.warning(f"Érvénytelen email cím: {email}")
                return False
        return True
