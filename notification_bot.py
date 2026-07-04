import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_URLS = [
    "https://www.mongar.gov.bt/",
    "https://www.mongar.gov.bt/tenders",
]
DEFAULT_STATE_PATH = Path(__file__).resolve().parent / "seen_tenders.json"


def load_state(state_path: Optional[Path] = None) -> Dict[str, bool]:
    path = state_path or DEFAULT_STATE_PATH
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state_path: Optional[Path] = None, state: Optional[Dict[str, bool]] = None) -> None:
    path = state_path or DEFAULT_STATE_PATH
    state = state or {}
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)


def extract_tender_items_from_html(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, str]] = []

    for item in soup.find_all(["item", "entry"]):
        title = " ".join(item.find("title").get_text(" ", strip=True).split()) if item.find("title") else ""
        link_tag = item.find("link")
        href = link_tag.get_text(" ", strip=True) if link_tag else ""
        if title and ("tender" in title.lower()):
            items.append({"title": title, "url": href})

    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        href = link["href"]
        lower_title = title.lower()
        lower_href = href.lower()
        is_tender_link = "tender" in lower_title or "tender" in lower_href
        is_announcement = "announcement" in lower_title or "announcement" in lower_href
        if is_tender_link and not is_announcement:
            items.append({"title": title, "url": href})

    return items


def fetch_page(url: str) -> str:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.text


def build_email_body(items: List[Dict[str, str]]) -> str:
    if not items:
        return "No new Mongar tenders were found."
    lines = ["New Mongar tender notifications:"]
    for item in items:
        title = item["title"] or "Untitled tender"
        url = item.get("url", "")
        lines.append(f"- {title}")
        if url:
            lines.append(f"  Link: {url}")
    return "\n".join(lines)


def create_github_issue(title: str, body: str) -> Optional[str]:
    repository = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repository or not token:
        return None

    response = requests.post(
        f"https://api.github.com/repos/{repository}/issues",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body},
        timeout=20,
    )
    if response.status_code >= 400:
        return None
    data = response.json()
    return data.get("html_url")


def send_telegram_message(message: str) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise RuntimeError("Telegram credentials are not configured")

    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        timeout=20,
    )
    response.raise_for_status()


def send_email(to_address: str, subject: str, body: str) -> None:
    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from_email = os.getenv("RESEND_FROM_EMAIL")
    if resend_api_key and resend_from_email:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_api_key}", "Content-Type": "application/json"},
            json={
                "from": resend_from_email,
                "to": [to_address],
                "subject": subject,
                "text": body,
            },
            timeout=20,
        )
        response.raise_for_status()
        return

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_address = os.getenv("MAIL_FROM", smtp_user or "notifications@example.com")

    if not smtp_host or not smtp_user or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    import smtplib
    from email.message import EmailMessage

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


def check_for_new_tenders(urls: Optional[List[str]] = None, state_path: Optional[Path] = None, to_address: Optional[str] = None) -> List[Dict[str, str]]:
    urls = urls or DEFAULT_URLS
    state_path = state_path or DEFAULT_STATE_PATH
    state = load_state(state_path)
    found_items: List[Dict[str, str]] = []

    for url in urls:
        html = fetch_page(url)
        items = extract_tender_items_from_html(html)
        for item in items:
            href = item["url"]
            if href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(url, href)
            if full_url not in state:
                state[full_url] = True
                found_items.append({"title": item["title"], "url": full_url})

    save_state(state_path, state)
    if found_items:
        message_body = build_email_body(found_items)
        if to_address:
            try:
                send_email(to_address, "New Mongar tenders found", message_body)
            except Exception:
                issue_url = create_github_issue(
                    "New Mongar tenders found",
                    message_body,
                )
                if issue_url:
                    print(f"Email delivery failed; created GitHub issue: {issue_url}")
                else:
                    print("Email delivery failed and no GitHub issue could be created")

        try:
            send_telegram_message(message_body)
        except Exception as exc:
            print(f"Telegram notification failed: {exc}")
    return found_items


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check Mongar tender pages and optionally email reminders")
    parser.add_argument("--url", action="append", default=[], help="Page URL to scan")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_PATH), help="Path to the state file")
    parser.add_argument("--to", dest="to_address", help="Email address to notify")
    args = parser.parse_args()

    items = check_for_new_tenders(urls=args.url or None, state_path=Path(args.state_file), to_address=args.to_address)
    if items:
        print(f"Found {len(items)} new tender(s).")
    else:
        print("No new tenders found.")
