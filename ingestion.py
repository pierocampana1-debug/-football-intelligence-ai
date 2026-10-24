import os
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from src.db import connect, init_db

load_dotenv()

API_BASE = "https://api.football-data.org/v4"
# Codes documented by football-data.org. Availability may depend on the account's plan.
COMPETITIONS = {
    "SA": "Serie A",
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
}

class DataImportError(RuntimeError):
    pass

def fetch_competition_matches(code: str, season: int, token: str):
    url = f"{API_BASE}/competitions/{code}/matches"
    response = requests.get(
        url,
        headers={"X-Auth-Token": token},
        params={"season": season},
        timeout=30,
    )
    if response.status_code == 403:
        raise DataImportError(
            f"{code}: accesso negato (403). La competizione/stagione potrebbe non essere inclusa nel tuo piano."
        )
    if response.status_code == 429:
        raise DataImportError(f"{code}: limite richieste raggiunto (429). Riprova più tardi.")
    if response.status_code >= 400:
        detail = response.text[:250].replace("\n", " ")
        raise DataImportError(f"{code}: errore HTTP {response.status_code}: {detail}")
    payload = response.json()
    return payload.get("matches", [])

def import_season(season: int, codes=None):
    token = os.getenv("FOOTBALL_DATA_TOKEN", "").strip()
    if not token or token == "inserisci_qui_il_tuo_token":
        raise DataImportError(
            "Token mancante. Registra un account su football-data.org, copia .env.example in .env e inserisci FOOTBALL_DATA_TOKEN."
        )

    init_db()
    selected = codes or list(COMPETITIONS.keys())
    summary = []
    with connect() as conn:
        for code in selected:
            try:
                matches = fetch_competition_matches(code, season, token)
                for item in matches:
                    home = item.get("homeTeam") or {}
                    away = item.get("awayTeam") or {}
                    score = item.get("score") or {}
                    full_time = score.get("fullTime") or {}
                    home_goals = full_time.get("home")
                    away_goals = full_time.get("away")
                    # A null score is expected for not-yet-played fixtures.
                    conn.execute("""
                        INSERT INTO matches (
                            match_id, competition_code, competition_name, season,
                            utc_date, status, home_team, away_team, home_goals,
                            away_goals, source, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(match_id) DO UPDATE SET
                            competition_code=excluded.competition_code,
                            competition_name=excluded.competition_name,
                            season=excluded.season,
                            utc_date=excluded.utc_date,
                            status=excluded.status,
                            home_team=excluded.home_team,
                            away_team=excluded.away_team,
                            home_goals=excluded.home_goals,
                            away_goals=excluded.away_goals,
                            fetched_at=excluded.fetched_at
                    """, (
                        item["id"], code, COMPETITIONS[code], season,
                        item.get("utcDate") or "", item.get("status") or "UNKNOWN",
                        home.get("name") or "Squadra casa",
                        away.get("name") or "Squadra ospite",
                        home_goals, away_goals, "football-data.org",
                        datetime.now(timezone.utc).isoformat()
                    ))
                summary.append({"code": code, "name": COMPETITIONS[code],
                                "count": len(matches), "error": None})
            except (requests.RequestException, ValueError, DataImportError) as exc:
                summary.append({"code": code, "name": COMPETITIONS[code],
                                "count": 0, "error": str(exc)})
        conn.commit()
    return summary

if __name__ == "__main__":
    # football-data.org season parameter is the starting year: e.g. 2026 for 2026/27.
    season_now = datetime.now().year
    # Before August, the current season usually began in the previous calendar year.
    if datetime.now().month < 7:
        season_now -= 1
    results = import_season(season_now)
    for row in results:
        if row["error"]:
            print(f"[ERRORE] {row['name']}: {row['error']}")
        else:
            print(f"[OK] {row['name']}: {row['count']} partite importate/aggiornate")
