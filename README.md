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
2. Set notification environment variables. The bot can send email via Resend or SMTP, and it can also post to Telegram:
   ```bash
   export RESEND_API_KEY=your-resend-api-key
   export RESEND_FROM_EMAIL=onboarding@resend.dev
   export TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   export TELEGRAM_CHAT_ID=your-telegram-chat-id
   ```
   Or with SMTP:
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
