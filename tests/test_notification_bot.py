import os
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
