import json
import time
import requests
import feedparser
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
SOURCES_CFG = json.loads((ROOT / "config/sources.json").read_text())
HEADERS = {"User-Agent": "KnowledgeMaster/1.0 (educational; contact@example.com)"}


# ── Wikipedia ──────────────────────────────────────────────────────────────

def fetch_wikipedia(topic: str) -> dict:
    cfg = SOURCES_CFG["sources"]["wikipedia"]
    if not cfg["enabled"]:
        return {}
    try:
        search_url = cfg["search_url"]
        params = {
            "action": "query", "list": "search",
            "srsearch": topic, "format": "json",
            "srlimit": 3
        }
        r = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return {}

        page_title = results[0]["title"]
        summary_url = f"{cfg['base_url']}/page/summary/{page_title.replace(' ', '_')}"
        time.sleep(1 / cfg["rate_limit_per_second"])
        s = requests.get(summary_url, headers=HEADERS, timeout=10).json()

        content_url = f"{cfg['base_url']}/page/sections/{page_title.replace(' ', '_')}"
        c = requests.get(content_url, headers=HEADERS, timeout=10).json()
        sections = []
        for sec in c.get("sections", [])[:6]:
            text = BeautifulSoup(sec.get("text", ""), "lxml").get_text()
            sections.append({"title": sec.get("title", ""), "text": text[:800]})

        return {
            "source": "wikipedia",
            "title": s.get("title", ""),
            "summary": s.get("extract", "")[:cfg["max_content_length"]],
            "url": s.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "sections": sections
        }
    except Exception as e:
        print(f"[content_fetcher] wikipedia error: {e}")
        return {}


# ── OpenAlex ───────────────────────────────────────────────────────────────

def fetch_openalex(topic: str) -> list:
    cfg = SOURCES_CFG["sources"]["openalex"]
    if not cfg["enabled"]:
        return []
    try:
        url = f"{cfg['base_url']}/works"
        params = {
            "search": topic,
            "per-page": cfg["max_results"],
            "filter": "is_oa:true",
            "mailto": cfg["email"]
        }
        time.sleep(1 / cfg["rate_limit_per_second"])
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        items = r.json().get("results", [])
        results = []
        for item in items:
            results.append({
                "source": "openalex",
                "title": item.get("title", ""),
                "abstract": (item.get("abstract_inverted_index") and
                             _reconstruct_abstract(item["abstract_inverted_index"])) or "",
                "url": item.get("primary_location", {}).get("landing_page_url", ""),
                "year": item.get("publication_year", ""),
                "cited_by": item.get("cited_by_count", 0)
            })
        return results
    except Exception as e:
        print(f"[content_fetcher] openalex error: {e}")
        return []


def _reconstruct_abstract(inv: dict) -> str:
    words = {}
    for word, positions in inv.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[k] for k in sorted(words))[:1000]


# ── RSS Feeds ──────────────────────────────────────────────────────────────

def fetch_rss(topic: str) -> list:
    cfg = SOURCES_CFG["sources"]["rss_feeds"]
    if not cfg["enabled"]:
        return []
    results = []
    topic_lower = topic.lower()
    for feed_cfg in cfg["feeds"]:
        try:
            time.sleep(1 / cfg["rate_limit_per_second"])
            feed = feedparser.parse(feed_cfg["url"])
            count = 0
            for entry in feed.entries:
                if count >= cfg["max_articles_per_feed"]:
                    break
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                if topic_lower in title.lower() or topic_lower in summary.lower():
                    results.append({
                        "source": f"rss_{feed_cfg['name']}",
                        "title": title,
                        "summary": BeautifulSoup(summary, "lxml").get_text()[:600],
                        "url": entry.get("link", ""),
                        "published": entry.get("published", "")
                    })
                    count += 1
        except Exception as e:
            print(f"[content_fetcher] rss {feed_cfg['name']} error: {e}")
    return results


# ── Archive.org ────────────────────────────────────────────────────────────

def fetch_archive(topic: str) -> list:
    cfg = SOURCES_CFG["sources"]["archive_org"]
    if not cfg["enabled"]:
        return []
    try:
        params = {
            "q": topic,
            "fl[]": ["identifier", "title", "description", "subject"],
            "rows": cfg["max_results"],
            "output": "json",
            "mediatype": "texts"
        }
        time.sleep(1 / cfg["rate_limit_per_second"])
        r = requests.get(cfg["search_url"], params=params, headers=HEADERS, timeout=10)
        docs = r.json().get("response", {}).get("docs", [])
        results = []
        for doc in docs:
            results.append({
                "source": "archive_org",
                "title": doc.get("title", ""),
                "description": str(doc.get("description", ""))[:600],
                "url": f"https://archive.org/details/{doc.get('identifier', '')}",
                "subject": doc.get("subject", [])
            })
        return results
    except Exception as e:
        print(f"[content_fetcher] archive.org error: {e}")
        return []


# ── Main ───────────────────────────────────────────────────────────────────

def fetch_all(topic: str) -> dict:
    print(f"[content_fetcher] Fetching content for: {topic}")
    wiki = fetch_wikipedia(topic)
    papers = fetch_openalex(topic)
    news = fetch_rss(topic)
    books = fetch_archive(topic)

    return {
        "topic": topic,
        "wikipedia": wiki,
        "academic_papers": papers,
        "news_articles": news,
        "books": books,
        "total_sources": (
            (1 if wiki else 0) + len(papers) + len(news) + len(books)
        )
    }


if __name__ == "__main__":
    data = fetch_all("Quantum Entanglement")
    print(json.dumps(data, indent=2))
