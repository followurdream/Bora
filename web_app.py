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
MAX_NEWS_ITEMS = 5
FALLBACK_IMAGE_URL = "https://images.unsplash.com/photo-1677442135722-5f6f3f8f38c4?auto=format&fit=crop&w=1200&q=60"


def fetch_google_news(query: str, max_items: int = MAX_NEWS_ITEMS) -> list[dict[str, str]]:
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
        raw_description = item.findtext("description", default="")
        description = clean_text(raw_description)
        image_url = extract_image_url(raw_description)

        if title and link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "source": source,
                    "description": description,
                    "image_url": image_url,
                }
            )
    return items


def extract_image_url(raw_html: str) -> str:
    if not raw_html:
        return ""
    match = re.search(r"<img[^>]+src=['\"]([^'\"]+)['\"]", raw_html, flags=re.IGNORECASE)
    return html.unescape(match.group(1)).strip() if match else ""


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


def prepare_news(query: str, max_items: int = MAX_NEWS_ITEMS) -> list[dict[str, str]]:
    prepared: list[dict[str, str]] = []
    for item in fetch_google_news(query, max_items=max_items):
        summary = summarize_text(item["title"], item["description"])
        prepared.append(
            {
                "title": item["title"],
                "title_ko": translate_to_korean(item["title"]),
                "summary_ko": translate_to_korean(summary),
                "link": item["link"],
                "source": item["source"] or "출처 미표기",
                "pub_date": format_pub_date(item["pub_date"]),
                "image_url": item["image_url"] or FALLBACK_IMAGE_URL,
            }
        )
    return prepared


def render_news_cards(news_items: list[dict[str, str]]) -> str:
    if not news_items:
        return "<p class='empty'>표시할 뉴스가 없습니다.</p>"

    cards = []
    for item in news_items:
        cards.append(
            f"""
            <article class='card'>
              <img class='thumb' src='{html.escape(item['image_url'])}' alt='news image' loading='lazy'/>
              <div class='content'>
                <h3>{html.escape(item['title_ko'])}</h3>
                <p class='origin-title'>원문: {html.escape(item['title'])}</p>
                <p class='summary'>{html.escape(item['summary_ko'])}</p>
                <div class='meta'>
                  <span>{html.escape(item['source'])}</span>
                  <span>{html.escape(item['pub_date'])}</span>
                </div>
                <a href='{html.escape(item['link'])}' target='_blank' rel='noopener noreferrer'>원문 보기</a>
              </div>
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
    :root {{
      --bg: #f3f6fb;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --accent: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); }}
    .container {{ max-width: 1060px; margin: 0 auto; padding: 32px 20px 56px; }}
    .hero {{ background: linear-gradient(135deg, #0f172a, #1e3a8a); color: white; border-radius: 18px; padding: 24px; margin-bottom: 20px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .hero p {{ margin: 0; color: #dbeafe; }}
    .tabs {{ display: flex; gap: 10px; margin-bottom: 16px; }}
    .tab-btn {{ border: 1px solid var(--line); background: white; border-radius: 999px; padding: 10px 16px; cursor: pointer; font-weight: 700; color: #1e293b; }}
    .tab-btn.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .grid {{ display: grid; gap: 14px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; display: grid; grid-template-columns: 220px 1fr; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06); }}
    .thumb {{ width: 100%; height: 100%; min-height: 170px; object-fit: cover; background: #cbd5e1; }}
    .content {{ padding: 16px 18px; }}
    .card h3 {{ margin: 0 0 8px; font-size: 20px; line-height: 1.35; }}
    .origin-title {{ margin: 0 0 8px; color: var(--muted); font-size: 13px; }}
    .summary {{ margin: 0 0 10px; line-height: 1.5; }}
    .meta {{ display: flex; gap: 10px; justify-content: space-between; color: var(--muted); font-size: 12px; margin-bottom: 12px; }}
    a {{ color: var(--accent); text-decoration: none; font-weight: 700; }}
    .empty {{ color: var(--muted); }}
    .count {{ color: #334155; font-size: 14px; margin: 8px 0 12px; }}
    @media (max-width: 768px) {{
      .card {{ grid-template-columns: 1fr; }}
      .thumb {{ height: 190px; }}
    }}
  </style>
</head>
<body>
  <div class='container'>
    <div class='hero'>
      <h1>AI 이미지 / 영상 뉴스 브리핑</h1>
      <p>해외 뉴스를 한국어로 요약/번역해 카테고리별 상위 5개만 빠르게 확인하세요.</p>
    </div>

    <div class='tabs'>
      <button class='tab-btn active' data-tab='image'>이미지 뉴스</button>
      <button class='tab-btn' data-tab='video'>영상 뉴스</button>
    </div>

    <section id='image' class='panel active'>
      <p class='count'>총 {len(image_news)}건</p>
      <div class='grid'>
        {image_cards}
      </div>
    </section>

    <section id='video' class='panel'>
      <p class='count'>총 {len(video_news)}건</p>
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
            image_news = prepare_news("AI image generation OR text-to-image", max_items=MAX_NEWS_ITEMS)
            video_news = prepare_news("AI video generation OR text-to-video", max_items=MAX_NEWS_ITEMS)
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
