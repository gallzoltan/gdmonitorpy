import requests
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from gdmodule.repository import GazetteRepository

logger = logging.getLogger(__name__)

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

    def send_email(self, to_recipients: List[str], cc_recipients: List[str] = None, bcc_recipients: List[str] = None):
        """Email küldése a megadott címre"""
        
        if not self._validate_recipients(to_recipients):
            return False

        url = f"http://{self.msg_server}:{self.msg_port}/api/v1/msg"
        headers = {
            "Content-Type": "application/json"
        }

        content_result = self.create_content()  # Tuple vagy string lehet

        if isinstance(content_result, tuple):
            body, gazette_ids = content_result
        else:
            body = content_result
            gazette_ids = []

        if not body or body == "Nincs új küldésre váró adat.":
            logger.warning("Nincs tartalom az email küldéséhez.")
            return False

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
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                logging.info("Message sent successfully!")
                self.repository.mark_all_sent_email(gazette_ids)
                logging.info("All gazettes marked as sent via email.")
                try:
                    if response.text.strip():  # Nem üres válasz
                        json_response = response.json()
                        logging.info("JSON Response: %s", json_response)
                    else:
                        logging.warning("Empty response received")
                except json.JSONDecodeError:
                    logging.error("Response is not valid JSON format")
                    logging.error("Raw response: %s", response.text)
            else:
                logging.error("Failed to send message. Status code: %d", response.status_code)
                logging.error("Response: %s", response.text)
        except requests.exceptions.RequestException as e:
            logging.error("An error occurred: %s", e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)

    def create_content(self) -> str:
        """Email tartalom létrehozása a közlöny adatokból"""
        gazettes = self.repository.get_gazettes_for_email()        

        if not gazettes:
            return "Nincs új küldésre váró adat."
        
        gazette_ids = []
        content = "<h2>IX. Fejezettel kapcsolatos kormányhatározatok</h2>\n"

        for gazette in gazettes:
            gazette_ids.append(gazette['id'])  # ID hozzáadása a listához
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