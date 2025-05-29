# Dividend Alert System

This project automatically tracks dividend payments for specified stocks and sends alerts via email and Telegram when new dividends are detected.

## Features

- Daily monitoring of dividend payments for specified stocks
- Email notifications for new dividends
- Telegram notifications for new dividends
- Google Sheets integration for tracking dividend history
- Automated daily execution via GitHub Actions

## Setup

1. Fork this repository
2. Add the following secrets to your GitHub repository (Settings → Secrets → Actions):
   - `ALERT_EMAIL`: Your email address for notifications
   - `APP_PASSWORD`: Your email app password
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - `SENDER_EMAIL`: Your email address
   - `SERVICE_ACCOUNT_FILE_JSON`: Your Google Service Account JSON credentials

## Configuration

The script monitors the following stocks by default:
- MSTY
- PLTY

To modify the list of stocks, edit the `TICKERS` list in `dividends_alert.py`.

## How it Works

The script runs daily at 9:00 UTC via GitHub Actions. It:
1. Fetches dividend data from Yahoo Finance
2. Compares with previous data to detect new dividends
3. Sends notifications via email and Telegram
4. Updates a Google Sheet with the latest dividend information

## Local Development

1. Clone the repository
2. Create a `.env` file with the required environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run the script: `python dividends_alert.py` 
