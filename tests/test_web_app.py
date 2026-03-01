import unittest
from unittest.mock import patch

from web_app import parse_google_news_rss, prepare_news, summarize_text, translate_to_korean


SAMPLE_RSS = """<?xml version='1.0' encoding='UTF-8'?>
<rss><channel>
  <item>
    <title>AI image model update released</title>
    <link>https://example.com/a</link>
    <pubDate>Mon, 02 Dec 2024 10:00:00 GMT</pubDate>
    <source>TechCrunch</source>
    <description>New features for creators and marketers.</description>
  </item>
</channel></rss>
"""


class NewsParsingTests(unittest.TestCase):
    def test_parse_google_news_rss(self):
        items = parse_google_news_rss(SAMPLE_RSS)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "AI image model update released")
        self.assertEqual(items[0]["source"], "TechCrunch")

    def test_summarize_text_truncates_long_text(self):
        long_description = "A" * 300
        summary = summarize_text("title", long_description)
        self.assertTrue(summary.endswith("..."))
        self.assertLessEqual(len(summary), 140)

    @patch("web_app.translate_to_korean", side_effect=lambda text: f"KO:{text}")
    @patch(
        "web_app.fetch_google_news",
        return_value=[
            {
                "title": "AI video generator launched",
                "link": "https://example.com/v",
                "pub_date": "Mon, 02 Dec 2024 10:00:00 GMT",
                "source": "The Verge",
                "description": "Startup announced a new model.",
            }
        ],
    )
    def test_prepare_news_includes_translated_fields(self, _mock_fetch, _mock_translate):
        news = prepare_news("ai")
        self.assertEqual(len(news), 1)
        self.assertTrue(news[0]["title_ko"].startswith("KO:"))
        self.assertIn("summary_ko", news[0])

    @patch("web_app.request.urlopen", side_effect=Exception("network blocked"))
    def test_translate_to_korean_fallbacks_to_original(self, _mock_urlopen):
        source = "AI image update"
        translated = translate_to_korean(source)
        self.assertEqual(translated, source)


if __name__ == "__main__":
    unittest.main()
