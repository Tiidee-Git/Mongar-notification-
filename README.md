# Mongar-notification-

A small Python bot that checks Mongar tender pages for new tender announcements and can email a reminder when something new is found.

## Features
- Scrapes tender-related links from Mongar pages
- Tracks previously seen tenders so it only emails about new items
- Sends an email notification through SMTP when a new tender appears

## Run locally
1. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
2. Set SMTP environment variables:
   ```bash
   export SMTP_HOST=smtp.example.com
   export SMTP_PORT=587
   export SMTP_USER=your-email@example.com
   export SMTP_PASSWORD=your-password
   export MAIL_FROM=your-email@example.com
   ```
3. Run the bot:
   ```bash
   python3 notification_bot.py --to you@example.com
   ```

## Tests
```bash
python3 -m unittest discover -s tests -v
```
