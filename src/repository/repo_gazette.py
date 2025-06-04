import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class GazetteRepository:
    """Magyar Közlöny adatbázis műveletek kezelése"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Adatbázis inicializálása, ha még nem létezik"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS gazettes (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            publication_date TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            download_date TEXT NOT NULL,
            analyzed INTEGER DEFAULT 0,
            relevant INTEGER DEFAULT 0,  
            sent_email INTEGER DEFAULT 0       
        );
        CREATE TABLE IF NOT EXISTS summary (
            id INTEGER PRIMARY KEY,
            gazette_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            FOREIGN KEY (gazette_id) REFERENCES gazettes(id)
        );           
        ''')
        
        conn.commit()
        conn.close()
    
    def is_already_downloaded(self, url: str) -> bool:
        """Ellenőrzi, hogy egy URL már le van-e töltve"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM gazettes WHERE url = ?", (url,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    def save_gazette(self, title: str, publication_date: str, url: str, filename: str) -> int:
        """Új közlöny mentése az adatbázisba"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            "INSERT INTO gazettes (title, publication_date, url, filename, download_date) VALUES (?, ?, ?, ?, ?)",
            (title, publication_date, url, filename, now)
        )
        
        gazette_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return gazette_id
    
    def get_unanalyzed_gazettes(self) -> List[Dict]:
        """Még nem elemzett közlönyök lekérése"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM gazettes WHERE analyzed = 0")
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    
    def mark_as_analyzed(self, gazette_id: int, is_relevant: bool = False):
        """Közlöny megjelölése elemzettként"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE gazettes SET analyzed = 1, relevant = ? WHERE id = ?",
            (1 if is_relevant else 0, gazette_id)
        )
        
        conn.commit()
        conn.close()
    
    def save_summary(self, gazette_id: int, summary: str):
        """Összefoglaló mentése"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO summary (gazette_id, summary) VALUES (?, ?)",
            (gazette_id, summary)
        )
        
        conn.commit()
        conn.close()