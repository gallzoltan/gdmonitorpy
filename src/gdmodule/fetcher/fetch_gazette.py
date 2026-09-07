import logging
import requests
import certifi
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from gdmodule.repository import GazetteRepository

logger = logging.getLogger(__name__)

class GazetteFetcher:
    """Magyar Közlöny letöltő osztály"""
    
    FEED_URL = "https://magyarkozlony.hu/feed"
    DB_FILE = "gazettes.db"
    DOWNLOAD_DIR = "downloads"

    # Könyvtárként megadott CERTIFICATE_PATH esetén ezt a fájlt keressük.
    CA_BUNDLE_FILE = "ca-bundle.pem"
    
    def __init__(self, 
                 feed_url:str,
                 db_path:str, 
                 download_path:str,
                 certificate_path: Optional[str] = None, 
                 base_dir: Optional[str] = None, 
                 since_date: Optional[str] = None):
        """
        Inicializálja a Magyar Közlöny letöltőt
        
        Args:
            base_dir: Alap könyvtár, ahol az adatbázist és letöltéseket tárolja
                     Ha nincs megadva, az aktuális munkakönyvtárat használja
        """
        
        self.FEED_URL = feed_url if feed_url else self.FEED_URL
        self.DB_PATH = db_path if db_path else self.DB_FILE
        self.DOWNLOAD_DIR = download_path if download_path else self.DOWNLOAD_DIR

        # Dátum szűrő beállítása
        self.since_date = None
        if since_date:
            try:
                self.since_date = datetime.strptime(since_date, "%Y-%m-%d")
                logger.info(f"Dátum szűrő beállítva: {since_date}")
            except ValueError:
                logger.error(f"Hibás dátum formátum: {since_date}. Használja a YYYY-MM-DD formátumot.")

        # Alapértelmezett könyvtár beállítása
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.cwd()
            
        # Adatbázis és letöltési könyvtár elérési útvonala
        self.db_path = self.base_dir / self.DB_PATH
        self.download_path = self.base_dir / self.DOWNLOAD_DIR
        
        # Letöltési könyvtár létrehozása, ha nem létezik
        if not self.download_path.exists():
            self.download_path.mkdir(parents=True)
            
        # Repository inicializálása
        self.repository = GazetteRepository(self.db_path)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.session.verify = self._resolve_ca_bundle(certificate_path)

    def _resolve_ca_bundle(self, certificate_path: Optional[str]) -> str:
        """Kiválasztja a TLS ellenőrzéshez használt CA köteget.

        Alapértelmezés a certifi nyilvános gyökértanúsítvány-készlete: a
        magyarkozlony.hu publikusan hitelesített tanúsítványt használ, ehhez
        nem kell saját köteg. Saját köteg akkor kell, ha a gép TLS-t bontó
        proxy mögött van; ilyenkor a CERTIFICATE_PATH mutasson a köteg
        fájlra vagy az azt tartalmazó könyvtárra.

        Figyelem: a kiszolgáló saját (leaf) tanúsítványa NEM alkalmas CA
        kötegnek, mert nem tartalmazza a kibocsátói láncot — a verifikáció
        "unable to get local issuer certificate" hibára fut vele.
        """
        if not certificate_path:
            return certifi.where()

        path = Path(certificate_path)
        if not path.is_absolute():
            path = self.base_dir / path
        if path.is_dir():
            path = path / self.CA_BUNDLE_FILE

        if path.is_file():
            logger.info("Saját CA köteg használata: %s", path)
            return str(path)

        logger.warning(
            "A megadott CA köteg nem található (%s), a certifi gyökértanúsítványai lesznek használva",
            path,
        )
        return certifi.where()

    def _parse_pub_date(self, pub_date_str: str) -> Optional[datetime]:
        """
        RSS pubDate string átalakítása datetime objektummá
        
        Args:
            pub_date_str: pubDate string (pl. "Mon, 26 May 2025 21:52:39 +0200")
            
        Returns:
            datetime objektum vagy None ha nem sikerült a feldolgozás
        """
        if not pub_date_str:
            return None
            
        try:
            # RFC 2822 formátum feldolgozása
            # "Mon, 26 May 2025 21:52:39 +0200" -> datetime
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(pub_date_str)
        except Exception as e:
            logger.warning(f"Nem sikerült feldolgozni a dátumot: {pub_date_str} - {e}")
            return None

    def fetch_feed(self) -> List[Dict]:
        """
        RSS feed letöltése és feldolgozása
        
        Returns:
            A Magyar Közlöny bejegyzések listája
        """
        try:
            response = self.session.get(self.FEED_URL, timeout=30)
            response.raise_for_status()
            
            # XML feldolgozása
            root = ET.fromstring(response.content)

            # Bejegyzések kinyerése (RSS formátum)
            entries = []
            items = root.findall('.//item')
            logger.info(f"Bejegyzések száma a feed-ben: {len(items)}")
            
            for item in items:
                title_elem = item.find('title')
                title = title_elem.text if title_elem is not None else ""
                
                # Csak a Magyar Közlöny bejegyzéseket szűrjük
                if "Magyar Közlöny" in title:
                    pubdate_elem = item.find('pubDate')
                    published_str = pubdate_elem.text if pubdate_elem is not None else ""
                    
                    # Dátum feldolgozása
                    published_date = self._parse_pub_date(published_str)
                    
                    # Dátum szűrés alkalmazása
                    if self.since_date and published_date:
                        if published_date.date() < self.since_date.date():
                            logger.debug(f"Kihagyás (régebbi): {title} - {published_date.date()}")
                            continue
                    
                    link_elem = item.find('link')
                    url = link_elem.text if link_elem is not None else ""
                    if "megtekintes" in url:
                        url = url.replace("megtekintes", "letoltes")
                    
                    entries.append({
                        'title': title,
                        'url': url,
                        'published': published_str,
                        'published_date': published_date
                    })
                    
                    logger.info(f"Magyar Közlöny találat: {title} - {published_date.date() if published_date else 'Ismeretlen dátum'}")
            
            logger.info(f"Összesen {len(entries)} Magyar Közlöny bejegyzés található")
            return entries
            
        except Exception as e:
            logger.error(f"Hiba történt az RSS feed lekérése közben: {e}")
            return []
    
    def is_already_downloaded(self, url: str) -> bool:
        return self.repository.is_already_downloaded(url)
    
    def download_gazette(self, entry: Dict) -> Tuple[bool, Optional[str]]:
        """
        Magyar Közlöny letöltése
        
        Args:
            entry: A letöltendő közlöny adatai
            
        Returns:
            Tuple (sikeres letöltés, fájlnév vagy None)
        """
        if self.is_already_downloaded(entry['url']):
            logger.info(f"A közlöny már le volt töltve: {entry['title']}")
            return False, None
        
        try:
            # PDF URL kinyerése (ha az entry['url'] nem közvetlenül PDF-re mutat)
            if entry['url'].endswith('.pdf'):
                pdf_url = entry['url']
            else:
                # Ha szükséges, itt lehet kiegészítő logika a PDF URL kinyeréséhez
                # a közlöny oldalából
                pdf_url = entry['url']
            
            # Fájlnév generálás a címből
            filename = self._generate_filename(entry['title'])
            filepath = self.download_path / filename
            
            # PDF letöltése
            response = self.session.get(pdf_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Mentés az adatbázisba
            self._save_to_database(entry, filename)
            
            # logger.info(f"Sikeresen letöltve: {entry['title']} -> {filename}")
            return True, filename
            
        except Exception as e:
            logger.error(f"Hiba történt a letöltés közben: {e}")
            return False, None
    
    def _generate_filename(self, title: str) -> str:
        """Fájlnév generálása a címből"""
        # Cím tisztítása fájlnévhez
        clean_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)
        clean_title = clean_title.replace(" ", "_")
        
        # Időbélyeg hozzáadása az egyediség érdekében
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        return f"{clean_title}_{timestamp}.pdf"
    
    def _save_to_database(self, entry: Dict, filename: str) -> None:
        self.repository.save_gazette(
            entry['title'], 
            entry['published'], 
            entry['url'], 
            filename
        )
    
    def fetch_new_gazettes(self) -> List[str]:
        """
        Új Magyar Közlönyök letöltése
        
        Returns:
            A sikeresen letöltött fájlok listája
        """
        downloaded_files = []
        
        # RSS feed letöltése
        entries = self.fetch_feed()
        
        if not entries:
            logger.warning("Nem találhatók Magyar Közlöny bejegyzések a feed-ben")
            return downloaded_files
        
        # Közlönyök letöltése, amelyek még nem voltak letöltve
        for entry in entries:
            success, filename = self.download_gazette(entry)
            if success and filename:
                downloaded_files.append(str(self.download_path / filename))
                
        return downloaded_files
