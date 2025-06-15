# Alap Python image használata
FROM python:3.11-slim

# Munkakönyvtár beállítása
WORKDIR /app

# Rendszer csomagok frissítése (opcionális)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Requirements fájl másolása és függőségek telepítése
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Alkalmazás fájljainak másolása
COPY . .

# Port megadása (ha szükséges)
# EXPOSE 8000

# Nem-root felhasználó létrehozása (biztonsági okokból)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Alkalmazás indítása
CMD ["python", "app.py"]
