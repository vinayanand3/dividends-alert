import os
import pandas as pd
import yfinance as yf
from datetime import datetime
import yagmail
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import logging

# --- Load .env secrets ---
load_dotenv()

ALERT_EMAIL = os.getenv("ALERT_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
TICKERS = ['MSTY', 'PLTY']
DATA_DIR = 'dividend_tracker'
LOG_DIR = 'logs'

# --- Setup directories ---
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Configure Logging ---
log_file = os.path.join(LOG_DIR, 'dividends_alert.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logging.info("------ Script started ------")

# --- Date filenames ---
today_str = datetime.today().strftime('%Y-%m-%d')
today_file_yf = os.path.join(DATA_DIR, f'dividend_data_yfinance_{today_str}.csv')

# --- Fetch Yahoo Finance Dividends ---
all_data = []
for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        dividends = stock.dividends.reset_index()
        dividends['Ticker'] = ticker
        all_data.append(dividends)
        logging.info(f"Fetched dividend data for {ticker}")
    except Exception as e:
        logging.error(f"Error fetching {ticker}: {e}")

df_yf_today = pd.concat(all_data) if all_data else pd.DataFrame(columns=["Date", "Dividends", "Ticker"])
df_yf_today.to_csv(today_file_yf, index=False)
logging.info(f"Saved today's data to {today_file_yf}")

# --- Compare with previous file ---
all_yf_files = sorted(f for f in os.listdir(DATA_DIR) if f.startswith('dividend_data_yfinance_'))
previous_yf_file = os.path.join(DATA_DIR, all_yf_files[-2]) if len(all_yf_files) > 1 else None
new_dividends_yf = pd.DataFrame()

if previous_yf_file:
    df_prev = pd.read_csv(previous_yf_file)
    merged = pd.merge(df_yf_today, df_prev, on=['Date', 'Dividends', 'Ticker'], how='outer', indicator=True)
    new_dividends_yf = merged[merged['_merge'] == 'left_only'][['Date', 'Dividends', 'Ticker']]
    logging.info(f"Compared with previous data: {previous_yf_file}")

# --- Send Alerts ---
yag = yagmail.SMTP(ALERT_EMAIL, APP_PASSWORD)

for _, row in new_dividends_yf.iterrows():
    msg = f"{row['Ticker']} has a new dividend: {row['Dividends']} on {row['Date']}"
    yag.send(to=ALERT_EMAIL, subject=f"Dividend Alert: {row['Ticker']}", contents=msg)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                  data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    logging.info(f"Sent alert for {row['Ticker']} - {row['Dividends']} on {row['Date']}")

# --- Update Google Sheet ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)

    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    sheet.clear()
    rows = [df_yf_today.columns.tolist()] + df_yf_today.astype(str).values.tolist()
    sheet.update(rows)
    logging.info(f"Updated Google Sheet: {GOOGLE_SHEET_NAME}")
except Exception as e:
    logging.error(f"Error updating Google Sheet: {e}")

logging.info("------ Script finished ------\n")
