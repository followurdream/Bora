from __future__ import annotations

import html
import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib import parse, request
import xml.etree.ElementTree as ET

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def fetch_google_news(query: str, max_items: int = 8) -> list[dict[str, str]]:
    params = parse.urlencode(
        {
            "q": query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
    )
    url = f"{GOOGLE_NEWS_RSS}?{params}"
    with request.urlopen(url, timeout=10) as response:  # nosec: B310
        xml_payload = response.read().decode("utf-8", errors="ignore")
    parsed = parse_google_news_rss(xml_payload)
    return parsed[:max_items]


def parse_google_news_rss(xml_payload: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_payload)
    items: list[dict[str, str]] = []

    for item in root.findall("./channel/item"):
        title = clean_text(item.findtext("title", default=""))
        link = clean_text(item.findtext("link", default=""))
        pub_date = clean_text(item.findtext("pubDate", default=""))
        source = clean_text(item.findtext("source", default=""))
        description = clean_text(item.findtext("description", default=""))

        if title and link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "source": source,
                    "description": description,
                }
            )
    return items


def clean_text(raw_text: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw_text or "")
    return html.unescape(text).strip()


def summarize_text(title: str, description: str) -> str:
    combined = f"{title}. {description}".strip()
    cleaned = re.sub(r"\s+", " ", combined)
    if len(cleaned) <= 140:
        return cleaned
    return cleaned[:137].rstrip() + "..."


def translate_to_korean(text: str) -> str:
    if not text.strip():
        return text

    params = parse.urlencode({"q": text, "langpair": "en|ko"})
    url = f"https://api.mymemory.translated.net/get?{params}"
    try:
        with request.urlopen(url, timeout=10) as response:  # nosec: B310
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("responseData", {}).get("translatedText", text)
    except Exception:
        return text


def format_pub_date(pub_date: str) -> str:
    if not pub_date:
        return "날짜 정보 없음"
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return pub_date


def prepare_news(query: str) -> list[dict[str, str]]:
    prepared: list[dict[str, str]] = []
    for item in fetch_google_news(query):
        summary = summarize_text(item["title"], item["description"])
        prepared.append(
            {
                "title": item["title"],
                "title_ko": translate_to_korean(item["title"]),
                "summary": summary,
                "summary_ko": translate_to_korean(summary),
                "link": item["link"],
                "source": item["source"] or "출처 미표기",
                "pub_date": format_pub_date(item["pub_date"]),
            }
        )
    return prepared


def render_news_cards(news_items: list[dict[str, str]]) -> str:
    if not news_items:
        return "<p>표시할 뉴스가 없습니다.</p>"

    cards = []
    for item in news_items:
        cards.append(
            f"""
            <article class='card'>
              <h3>{html.escape(item['title_ko'])}</h3>
              <p class='origin-title'>원문: {html.escape(item['title'])}</p>
              <p>{html.escape(item['summary_ko'])}</p>
              <div class='meta'>
                <span>{html.escape(item['source'])}</span>
                <span>{html.escape(item['pub_date'])}</span>
              </div>
              <a href='{html.escape(item['link'])}' target='_blank' rel='noopener noreferrer'>원문 보기</a>
            </article>
            """
        )
    return "\n".join(cards)


def render_page(image_news: list[dict[str, str]], video_news: list[dict[str, str]]) -> str:
    image_cards = render_news_cards(image_news)
    video_cards = render_news_cards(video_news)
    return f"""<!doctype html>
<html lang='ko'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width,initial-scale=1' />
  <title>AI 이미지/영상 뉴스 브리핑</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f6f8fb; color: #111827; }}
    .container {{ max-width: 980px; margin: 0 auto; padding: 28px 20px 50px; }}
    h1 {{ margin-bottom: 8px; }}
    .desc {{ color: #4b5563; margin-bottom: 20px; }}
    .tabs {{ display: flex; gap: 8px; margin-bottom: 20px; }}
    .tab-btn {{ border: 1px solid #d1d5db; background: white; border-radius: 10px; padding: 10px 14px; cursor: pointer; font-weight: 600; }}
    .tab-btn.active {{ background: #111827; color: white; border-color: #111827; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .grid {{ display: grid; gap: 14px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); }}
    .card h3 {{ margin: 0 0 8px; font-size: 18px; }}
    .origin-title {{ margin: 0 0 10px; color: #6b7280; font-size: 13px; }}
    .meta {{ display: flex; justify-content: space-between; color: #6b7280; font-size: 12px; margin-top: 10px; margin-bottom: 10px; }}
    a {{ color: #2563eb; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <div class='container'>
    <h1>AI 이미지 / 영상 뉴스 브리핑</h1>
    <p class='desc'>해외 뉴스를 한국어로 번역해 핵심만 깔끔하게 정리한 페이지입니다.</p>

    <div class='tabs'>
      <button class='tab-btn active' data-tab='image'>이미지</button>
      <button class='tab-btn' data-tab='video'>영상</button>
    </div>

    <section id='image' class='panel active'>
      <div class='grid'>
        {image_cards}
      </div>
    </section>

    <section id='video' class='panel'>
      <div class='grid'>
        {video_cards}
      </div>
    </section>
  </div>

  <script>
    const buttons = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.panel');
    buttons.forEach((button) => {{
      button.addEventListener('click', () => {{
        buttons.forEach((b) => b.classList.remove('active'));
        panels.forEach((p) => p.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
      }});
    }});
  </script>
</body>
</html>
"""


class NewsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        try:
            image_news = prepare_news("AI image generation OR text-to-image")
            video_news = prepare_news("AI video generation OR text-to-video")
            body = render_page(image_news, video_news)
            self._send_html(body)
        except Exception as exc:  # pragma: no cover
            self._send_html(f"<h1>오류</h1><pre>{html.escape(str(exc))}</pre>", status=500)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = HTTPServer((host, port), NewsHandler)
    print(f"AI News briefing is running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
