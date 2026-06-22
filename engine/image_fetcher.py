import json
import time
import requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
CFG = json.loads((ROOT / "config/settings.json").read_text())
SOURCES = json.loads((ROOT / "config/sources.json").read_text())
HEADERS = {"User-Agent": "KnowledgeMaster/1.0 (educational; contact@example.com)"}
ALLOWED = set(SOURCES["sources"]["wikimedia"]["allowed_formats"])


def fetch_wikimedia_images(topic: str, subtopics: list = None) -> list:
    cfg = SOURCES["sources"]["wikimedia"]
    if not cfg["enabled"]:
        return []

    queries = [topic] + (subtopics[:3] if subtopics else [])
    images = []
    seen = set()

    for query in queries:
        if len(images) >= CFG["content"]["image_per_topic"]:
            break
        try:
            time.sleep(1 / cfg["rate_limit_per_second"])
            params = {
                "action": "query",
                "generator": "search",
                "gsrnamespace": 6,
                "gsrsearch": f"filetype:bitmap|drawing {query}",
                "gsrlimit": 10,
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
                "format": "json"
            }
            r = requests.get(cfg["base_url"], params=params, headers=HEADERS, timeout=10)
            pages = r.json().get("query", {}).get("pages", {})

            for page in pages.values():
                if len(images) >= CFG["content"]["image_per_topic"]:
                    break
                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                info = info_list[0]
                url = info.get("url", "")
                ext = url.rsplit(".", 1)[-1].lower()
                if ext not in ALLOWED:
                    continue
                if url in seen:
                    continue

                meta = info.get("extmetadata", {})
                license_name = meta.get("LicenseShortName", {}).get("value", "")
                artist = meta.get("Artist", {}).get("value", "")
                description = meta.get("ImageDescription", {}).get("value", "")

                if not _is_free_license(license_name):
                    continue

                seen.add(url)
                images.append({
                    "url": url,
                    "title": page.get("title", "").replace("File:", ""),
                    "license": license_name,
                    "artist": _clean_html(artist),
                    "description": _clean_html(description)[:300],
                    "width": info.get("width", 0),
                    "height": info.get("height", 0),
                    "source_query": query
                })
        except Exception as e:
            print(f"[image_fetcher] wikimedia error for '{query}': {e}")

    return images[:CFG["content"]["image_per_topic"]]


def _is_free_license(license: str) -> bool:
    free_keywords = ["cc", "public domain", "pd", "cc0", "cc-by", "cc-sa"]
    l = license.lower()
    return any(k in l for k in free_keywords)


def _clean_html(text: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(text, "lxml").get_text().strip()


def run(topic: str, subtopics: list = None) -> list:
    images = fetch_wikimedia_images(topic, subtopics)
    print(f"[image_fetcher] Found {len(images)} images for: {topic}")
    return images


if __name__ == "__main__":
    imgs = run("Quantum Entanglement", ["photon", "superposition", "Bell theorem"])
    print(json.dumps(imgs, indent=2))
