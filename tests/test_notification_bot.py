import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import notification_bot


class NotificationBotTests(unittest.TestCase):
    def test_extract_tender_items_filters_mongar_matches(self):
        html = """
        <html>
          <body>
            <a href='https://example.com/tender-1'>Tender for road works in Mongar</a>
            <a href='https://example.com/other'>General announcement</a>
            <a href='https://example.com/tender-2'>Tender for school construction</a>
          </body>
        </html>
        """
        items = notification_bot.extract_tender_items_from_html(html)
        self.assertEqual(len(items), 2)
        self.assertTrue(all('tender' in item['title'].lower() for item in items))
        self.assertTrue(any('mongar' in item['title'].lower() for item in items))

    def test_state_file_records_seen_tenders(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "seen.json"
            state = notification_bot.load_state(state_path)
            notification_bot.save_state(state_path, {"https://example.com/tender": True})
            reloaded = notification_bot.load_state(state_path)
            self.assertTrue(reloaded["https://example.com/tender"])

    def test_extract_tender_items_from_rss_feed(self):
        rss = """
        <?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Tender for Mongar road works</title>
              <link>https://example.com/tender-rss</link>
            </item>
          </channel>
        </rss>
        """
        items = notification_bot.extract_tender_items_from_html(rss)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Tender for Mongar road works")

    @patch("notification_bot.requests.post")
    def test_send_email_uses_resend_when_configured(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "msg_123"}

        with patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM_EMAIL": "sender@example.com"}, clear=False):
            notification_bot.send_email("recipient@example.com", "Subject", "Body")

        self.assertTrue(mock_post.called)

    @patch("notification_bot.requests.post")
    def test_create_github_issue_posts_to_repository_api(self, mock_post):
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"html_url": "https://example.com/issues/1"}

        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_TOKEN": "token"}, clear=False):
            issue_url = notification_bot.create_github_issue("Title", "Body")

        self.assertEqual(issue_url, "https://example.com/issues/1")
        self.assertTrue(mock_post.called)


if __name__ == "__main__":
    unittest.main()
