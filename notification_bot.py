import json
import os
import re
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


def send_email(to_address: str, subject: str, body: str) -> None:
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
    if found_items and to_address:
        send_email(to_address, "New Mongar tenders found", build_email_body(found_items))
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
