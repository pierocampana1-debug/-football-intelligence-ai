from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from src.db import connect, init_db
from src.model import estimate_lambdas, predict_match, double_chance, MODEL_VERSION
from src.ingestion import import_season, COMPETITIONS, DataImportError

st.set_page_config(page_title="Football Intelligence AI", page_icon="⚽", layout="wide")
init_db()

st.title("⚽ Football Intelligence AI")
st.caption("Prototipo statistico personale · dati reali solo dopo l'importazione · nessuna previsione garantita")

def read_matches():
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM matches ORDER BY utc_date DESC", conn)

df = read_matches()

with st.sidebar:
    st.header("Dati")
    st.write("Fonte: football-data.org API v4")
    season_default = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
    season = st.number_input("Anno iniziale stagione", min_value=2000, max_value=2100,
                             value=season_default, step=1,
                             help="Esempio: 2026 per la stagione 2026/27.")
    if st.button("Aggiorna dati da API", type="primary", use_container_width=True):
        with st.spinner("Scaricamento in corso..."):
            try:
                summary = import_season(int(season))
                for item in summary:
                    if item["error"]:
                        st.error(f'{item["name"]}: {item["error"]}')
                    else:
                        st.success(f'{item["name"]}: {item["count"]} partite importate/aggiornate')
                st.rerun()
            except DataImportError as exc:
                st.error(str(exc))
    st.caption("Serve un token API nel file .env. Il token non è incluso nel pacchetto.")
    st.divider()
    st.write("Non inserire mai credenziali nel codice o in screenshot pubblici.")

if df.empty:
    st.warning("Il database è vuoto. Configura il token API e premi «Aggiorna dati da API». Nessun dato o pronostico fittizio viene mostrato.")
    st.markdown("""
    **Per iniziare**
    1. Registrati su [football-data.org](https://www.football-data.org/client/register).
    2. Copia `.env.example` in un file chiamato `.env`.
    3. Incolla il tuo token dopo `FOOTBALL_DATA_TOKEN=`.
    4. Riavvia l'app e premi **Aggiorna dati da API**.
    """)
    st.stop()

df["utc_date"] = pd.to_datetime(df["utc_date"], utc=True, errors="coerce")
st.sidebar.success(f"{len(df)} partite nel database")

competitions = sorted(df["competition_name"].dropna().unique().tolist())
chosen_comp = st.selectbox("Campionato", competitions)
comp_df = df[df["competition_name"] == chosen_comp].copy()
finished = comp_df[(comp_df["status"] == "FINISHED") &
                   comp_df["home_goals"].notna() & comp_df["away_goals"].notna()].copy()
upcoming = comp_df[comp_df["status"].isin(["SCHEDULED", "TIMED"])].sort_values("utc_date")

m1, m2, m3 = st.columns(3)
m1.metric("Partite archiviate", len(comp_df))
m2.metric("Partite concluse", len(finished))
m3.metric("Prossime partite", len(upcoming))

st.subheader("Prossime partite e probabilità")
if upcoming.empty:
    st.info("Non risultano partite future con stato SCHEDULED/TIMED per questo campionato nei dati importati.")
else:
    options = {
        f'{r["utc_date"].strftime("%d/%m/%Y %H:%M UTC")} · {r["home_team"]} - {r["away_team"]}': int(r["match_id"])
        for _, r in upcoming.iterrows() if pd.notna(r["utc_date"])
    }
    if not options:
        st.info("Le date delle prossime partite non sono leggibili.")
    else:
        selected_label = st.selectbox("Seleziona partita", list(options.keys()))
        match_id = options[selected_label]
        match = comp_df[comp_df["match_id"] == match_id].iloc[0]
        try:
            lam_h, lam_a, n_h, n_a = estimate_lambdas(finished, match["home_team"], match["away_team"])
            pred = predict_match(lam_h, lam_a)
            dc = double_chance(pred)
            a, b = st.columns(2)
            a.metric("Gol attesi casa (λ)", f"{lam_h:.2f}", help=f"Partite casalinghe osservate per la squadra: {n_h}")
            b.metric("Gol attesi ospite (λ)", f"{lam_a:.2f}", help=f"Partite in trasferta osservate per la squadra: {n_a}")
            st.markdown("#### Mercato 1X2")
            c1, c2, c3 = st.columns(3)
            c1.metric("1 · Casa", f'{pred["p_home"]:.1%}')
            c2.metric("X · Pareggio", f'{pred["p_draw"]:.1%}')
            c3.metric("2 · Ospite", f'{pred["p_away"]:.1%}')
            c1, c2 = st.columns(2)
            c1.metric("Over 2,5", f'{pred["p_over25"]:.1%}')
            c2.metric("Under 2,5", f'{pred["p_under25"]:.1%}')
            c1, c2 = st.columns(2)
            c1.metric("Goal (entrambe segnano)", f'{pred["p_btts_yes"]:.1%}')
            c2.metric("No Goal", f'{pred["p_btts_no"]:.1%}')
            st.markdown("#### Doppia chance")
            c1, c2, c3 = st.columns(3)
            c1.metric("1X", f'{dc["1X"]:.1%}')
            c2.metric("X2", f'{dc["X2"]:.1%}')
            c3.metric("12", f'{dc["12"]:.1%}')
            st.markdown("#### Risultati esatti più probabili")
            matrix = pred["matrix"]
            scores = []
            for i, row in enumerate(matrix):
                for j, p in enumerate(row):
                    scores.append({"Risultato": f"{i}-{j}", "Probabilità": p})
            score_df = pd.DataFrame(scores).sort_values("Probabilità", ascending=False).head(10)
            score_df["Probabilità"] = score_df["Probabilità"].map(lambda x: f"{x:.2%}")
            st.dataframe(score_df, use_container_width=True, hide_index=True)
            st.caption(f"Risultato singolo più probabile: {pred['most_likely_score']} ({pred['score_probability']:.2%}). Versione modello: {MODEL_VERSION}.")
            with connect() as conn:
                conn.execute("""
                    INSERT INTO predictions (
                        match_id, model_version, lambda_home, lambda_away,
                        p_home, p_draw, p_away, p_over25, p_under25,
                        p_btts_yes, p_btts_no, most_likely_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (match_id, MODEL_VERSION, lam_h, lam_a,
                      pred["p_home"], pred["p_draw"], pred["p_away"],
                      pred["p_over25"], pred["p_under25"], pred["p_btts_yes"],
                      pred["p_btts_no"], pred["most_likely_score"]))
                conn.commit()
        except ValueError as exc:
            st.warning(f"Non posso calcolare una previsione: {exc}")

st.subheader("Storico recente")
show_cols = ["utc_date", "home_team", "away_team", "home_goals", "away_goals", "status"]
recent = comp_df.sort_values("utc_date", ascending=False)[show_cols].head(30).copy()
recent["utc_date"] = recent["utc_date"].dt.strftime("%Y-%m-%d %H:%M UTC")
st.dataframe(recent, use_container_width=True, hide_index=True)

with st.expander("Limiti importanti del prototipo"):
    st.markdown("""
    - Il modello Poisson è una baseline didattica, non un sistema validato per scommettere.
    - Non include ancora xG, infortuni, formazioni, quote né correzioni Dixon–Coles.
    - Il piano API può non includere tutti i campionati o tutte le stagioni: errori e limitazioni sono mostrati, non aggirati.
    - Le probabilità non sono garanzie e non devono essere interpretate come consigli finanziari.
    - Le previsioni registrate durante una consultazione non costituiscono ancora un backtest rigoroso: per quello serve salvare automaticamente ogni previsione prima del calcio d'inizio.
    """)
