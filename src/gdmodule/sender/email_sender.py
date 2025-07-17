import requests
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from gdmodule.repository import GazetteRepository

logger = logging.getLogger(__name__)

class EmailSender:
    """Email küldő osztály a Magyar Közlöny elemzésekhez"""

    def __init__(self, msg_server: str, msg_port: int, db_path: Path):
        self.msg_server = msg_server
        self.msg_port = msg_port
        self.repository = GazetteRepository(db_path)

    def send_email(self, to_recipients: List[str] = None, cc_recipients: List[str] = None, bcc_recipients: List[str] = None):
        """Email küldése a megadott címre"""
        url = f"http://{self.msg_server}:{self.msg_port}/api/v1/msg"
        headers = {
            "Content-Type": "application/json"
        }
        subject = "IX. Fejezettel kapcsolatos kormányhatározatok összefoglalója"
        body = self.create_content()
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
            print(f"Status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text}")
            if response.status_code == 200:
                logging.info("Message sent successfully!")
                self.repository.mark_all_sent_email()
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
        content = "Kedves Felhasználó,\n\n"
        content += "Az alábbi Magyar Közlönyök elemzése megtörtént:\n\n"
        for gazette in gazettes:    
            content += f"**{gazette['title']}**\n\n"
            content += f"Megjelenés dátuma: {gazette['publication_date']}\n"
            content += f"URL: {gazette['url']}\n"
            content += f"Kormányhatározat száma: {gazette['gdecision_title']}\n\n"
            content += f"Relevancia pontszám: {gazette['relevant_score']}\n"
            content += f"Kulcsszó egyezések: {gazette['keyword_matches']}\n"
            content += f"Összefoglaló: {gazette['summary']}\n\n"
        return content