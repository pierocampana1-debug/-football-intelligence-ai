# Football Intelligence AI — prototipo gratuito

Applicazione Python + SQLite + Streamlit per importare partite da football-data.org e calcolare probabilità illustrative con un modello Poisson semplice.

## Cosa include
- Database SQLite creato automaticamente in `data/football.db`
- Importazione partite tramite API v4 di football-data.org
- Competizioni configurate: Serie A (`SA`), Premier League (`PL`), La Liga (`PD`), Bundesliga (`BL1`), Ligue 1 (`FL1`)
- Modello Poisson per 1X2, Over/Under 2,5, Goal/No Goal, doppia chance e risultati esatti
- Dashboard Streamlit e test automatici del modello

## Requisiti
Python 3.11 o più recente consigliato. Streamlit documenta l'installazione con `pip` e l'avvio tramite `streamlit run app.py`: https://docs.streamlit.io/get-started/installation

## 1. Scarica ed estrai il pacchetto
Estrai lo ZIP in una cartella facile da trovare, per esempio `football_intelligence_ai`.

## 2. Apri il terminale nella cartella del progetto

### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Se PowerShell impedisce l'attivazione dell'ambiente, puoi usare il Prompt dei comandi:
```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Ottieni e configura il token API
1. Crea un account su https://www.football-data.org/client/register
2. Leggi i limiti e i termini del piano su https://www.football-data.org/pricing
3. Apri il file `.env` con un editor di testo.
4. Sostituisci `inserisci_qui_il_tuo_token` con il token assegnato al tuo account:
   `FOOTBALL_DATA_TOKEN=IL_TUO_TOKEN_REALE`
5. Salva il file. Non condividere il token e non caricare `.env` su GitHub.

**Serve un token API.** Non è incluso in questo pacchetto e non ne viene inventato uno. Il piano gratuito potrebbe non consentire tutte le competizioni/stagioni: l'app mostrerà gli errori ricevuti dall'API.

## 4. Avvia la dashboard
Dalla cartella del progetto, con l'ambiente virtuale attivo:
```bash
python -m streamlit run app.py
```
Il browser dovrebbe aprire la dashboard. Se non si apre, copia nel browser l'indirizzo locale mostrato nel terminale.

Premi **Aggiorna dati da API**. Il primo download può richiedere alcuni secondi. Se una competizione restituisce 403, controlla la copertura del piano API; non significa necessariamente che il codice sia rotto.

## 5. Esegui i test
```bash
python -m unittest discover -s tests
```

## 6. Aggiornamento automatico giornaliero
Il file `jobs/daily_update.py` importa la stagione corrente. Per ora va programmato con il sistema operativo:
- Windows: Utilità di pianificazione (Task Scheduler)
- macOS/Linux: `cron`

Il comando da eseguire è il percorso del Python dell'ambiente virtuale seguito dal percorso assoluto di `jobs/daily_update.py`. Eseguilo dalla cartella del progetto. La macchina deve essere accesa e connessa a Internet. Non è ancora configurato un servizio cloud.

## Fonte dati e documentazione
- API quickstart: https://www.football-data.org/documentation/quickstart
- API reference: https://www.football-data.org/documentation/api
- Prezzi/limiti: https://www.football-data.org/pricing

La API usa l'header `X-Auth-Token` e gli endpoint v4. Il parametro `season` usa l'anno di inizio stagione, ad esempio `2026` per 2026/27.

## Limiti noti
- Il modello è una baseline didattica: non è validato per profitto e non garantisce pronostici corretti.
- Le statistiche xG, assenze, formazioni e quote non sono ancora integrate.
- La dashboard calcola una previsione quando selezioni una partita futura e la salva in tabella. Questo non equivale a un backtest corretto, perché il salvataggio dipende dalla consultazione. La prossima fase dovrebbe creare automaticamente snapshot delle probabilità prima del calcio d'inizio.
- La copertura dei dati dipende dal piano API e dalla competizione.
