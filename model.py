import math
import pandas as pd

MODEL_VERSION = "poisson-baseline-0.1"

def poisson_pmf(lam: float, k: int) -> float:
    if lam < 0:
        raise ValueError("lambda deve essere >= 0")
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def estimate_lambdas(history: pd.DataFrame, home_team: str, away_team: str,
                     min_matches: int = 3, shrinkage: float = 5.0):
    """
    Baseline interpretabile: medie gol casa/trasferta con shrinkage verso
    la media del campionato. Usa esclusivamente partite concluse presenti
    nello storico. Non è un modello calibrato professionalmente.
    """
    if history.empty:
        raise ValueError("Non ci sono partite concluse per questo campionato.")

    h = history.dropna(subset=["home_goals", "away_goals"]).copy()
    if h.empty:
        raise ValueError("Lo storico non contiene risultati finali validi.")
    h["home_goals"] = pd.to_numeric(h["home_goals"])
    h["away_goals"] = pd.to_numeric(h["away_goals"])

    league_home = float(h["home_goals"].mean())
    league_away = float(h["away_goals"].mean())
    if league_home <= 0 or league_away <= 0:
        raise ValueError("Media gol del campionato non valida.")

    home_rows = h[h["home_team"] == home_team]
    away_rows = h[h["away_team"] == away_team]

    # Shrink team means toward league means to reduce extreme estimates
    # when a team has only a few observations.
    home_scored = (home_rows["home_goals"].sum() + shrinkage * league_home) / (len(home_rows) + shrinkage)
    home_conceded = (home_rows["away_goals"].sum() + shrinkage * league_away) / (len(home_rows) + shrinkage)
    away_scored = (away_rows["away_goals"].sum() + shrinkage * league_away) / (len(away_rows) + shrinkage)
    away_conceded = (away_rows["home_goals"].sum() + shrinkage * league_home) / (len(away_rows) + shrinkage)

    # Geometric mean of scoring strength and opponent's concession rate.
    lam_home = math.sqrt(max(home_scored, 0.01) * max(away_conceded, 0.01))
    lam_away = math.sqrt(max(away_scored, 0.01) * max(home_conceded, 0.01))
    return max(0.05, min(lam_home, 5.0)), max(0.05, min(lam_away, 5.0)), len(home_rows), len(away_rows)

def predict_match(lam_home: float, lam_away: float, max_goals: int = 10):
    matrix = [[poisson_pmf(lam_home, i) * poisson_pmf(lam_away, j)
               for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    p_home = sum(matrix[i][j] for i in range(max_goals + 1)
                 for j in range(max_goals + 1) if i > j)
    p_draw = sum(matrix[i][j] for i in range(max_goals + 1)
                 for j in range(max_goals + 1) if i == j)
    p_away = sum(matrix[i][j] for i in range(max_goals + 1)
                 for j in range(max_goals + 1) if i < j)
    p_over25 = sum(matrix[i][j] for i in range(max_goals + 1)
                   for j in range(max_goals + 1) if i + j >= 3)
    p_btts = sum(matrix[i][j] for i in range(1, max_goals + 1)
                 for j in range(1, max_goals + 1))
    score = max(
        ((i, j, matrix[i][j]) for i in range(max_goals + 1)
         for j in range(max_goals + 1)),
        key=lambda x: x[2]
    )
    return {
        "p_home": p_home, "p_draw": p_draw, "p_away": p_away,
        "p_over25": p_over25, "p_under25": 1.0 - p_over25,
        "p_btts_yes": p_btts, "p_btts_no": 1.0 - p_btts,
        "most_likely_score": f"{score[0]}-{score[1]}",
        "score_probability": score[2],
        "matrix": matrix,
    }

def double_chance(prediction):
    return {
        "1X": prediction["p_home"] + prediction["p_draw"],
        "X2": prediction["p_draw"] + prediction["p_away"],
        "12": prediction["p_home"] + prediction["p_away"],
    }
