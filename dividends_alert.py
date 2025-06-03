import os
import pandas as pd
import yfinance as yf
from datetime import datetime
import smtplib
from email.message import EmailMessage
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import logging

# --- Load .env secrets ---
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
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

# --- Email Utility ---
def send_email(subject, body, to_list):
    if not SENDER_EMAIL or not APP_PASSWORD:
        logging.error("Missing SENDER_EMAIL or APP_PASSWORD! Skipping email.")
        return

    if not to_list:
        logging.error("No ALERT_EMAIL configured. Skipping email.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(to_list)
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)

# --- Send Alerts ---
recipient_list = [email.strip() for email in ALERT_EMAIL.split(",")] if ALERT_EMAIL else []
if not recipient_list:
    logging.warning("ALERT_EMAIL not set; email notifications will be skipped.")

if not SENDER_EMAIL or not APP_PASSWORD:
    logging.warning("Email credentials are missing; email notifications will fail.")


if not new_dividends_yf.empty:
    for _, row in new_dividends_yf.iterrows():
        msg = f"{row['Ticker']} has a new dividend: {row['Dividends']} on {row['Date']}\n\n📊 View Sheet: {GOOGLE_SHEET_URL}"
        send_email(subject=f"Dividend Alert: {row['Ticker']}", body=msg, to_list=recipient_list)
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        )
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
else:
    logging.info("No new dividends found today.")

logging.info("------ Script finished ------\n")
