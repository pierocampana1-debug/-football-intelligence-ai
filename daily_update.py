"""Da eseguire una volta al giorno tramite Utilità di pianificazione/cron."""
from datetime import datetime
from src.ingestion import import_season

season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
for item in import_season(season):
    if item["error"]:
        print(f'[ERRORE] {item["name"]}: {item["error"]}')
    else:
        print(f'[OK] {item["name"]}: {item["count"]} partite')
