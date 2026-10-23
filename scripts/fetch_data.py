"""Download the raw data and save it under data/raw/ (commit these files).

Sources
- Wikipedia (CC BY-SA 4.0): plain-text articles for the breeds in data/wiki_breeds.txt
- dogapi.dog (MIT): structured breed facts (weight, life span, group, hypoallergenic)

Run:  uv run python -m scripts.fetch_data
"""
import json
import os
import re
import sys
import time

import httpx

from app.core import config

WIKI_API = "https://en.wikipedia.org/w/api.php"
DOGAPI = "https://dogapi.dog/api/v2"


def user_agent() -> str:
    """Wikimedia's User-Agent policy (https://w.wiki/4wJS) requires contact info,
    otherwise requests are blocked with 403. Set WIKI_CONTACT in .env."""
    contact = os.environ.get("WIKI_CONTACT", "").strip()
    if not contact or "@" not in contact and "://" not in contact:
        sys.exit("Set WIKI_CONTACT in .env to your email (or your GitHub repo URL). "
                 "Wikipedia blocks requests that have no contact information.")
    return f"DogBreedAdvisor/0.1 ({contact}; student capstone project) httpx/{httpx.__version__}"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def read_breed_list() -> list[tuple[str, str]]:
    pairs = []
    for line in config.BREED_LIST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        title, _, name = line.partition("|")
        pairs.append((title.strip(), (name or title).strip()))
    return pairs


def fetch_wikipedia(client: httpx.Client) -> int:
    config.WIKI_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for title, breed in read_breed_list():
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "extracts|info",
            "inprop": "url",
            "explaintext": "1",
            "exsectionformat": "wiki",   # keeps "== Heading ==" lines so we know sections
            "redirects": "1",
            "titles": title,
        }
        resp = client.get(WIKI_API, params=params)
        if resp.status_code == 429:          # rate-limited: wait and retry once
            time.sleep(5)
            resp = client.get(WIKI_API, params=params)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", [])
        page = pages[0] if pages else {}
        text = page.get("extract", "")
        if page.get("missing") or len(text) < 500:
            print(f"  WARNING: '{title}' not found or too short - check the title in {config.BREED_LIST_FILE.name}")
            continue
        record = {
            "breed": breed,
            "title": page["title"],
            "url": page.get("fullurl", f"https://en.wikipedia.org/wiki/{page['title'].replace(' ', '_')}"),
            "license": "CC BY-SA 4.0 (Wikipedia)",
            "text": text,
        }
        out = config.WIKI_DIR / f"{slugify(breed)}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        ok += 1
        print(f"  {breed:32s} {len(text.split()):6d} words")
        time.sleep(1.0)   # be polite to Wikipedia
    return ok


def fetch_dogapi(client: httpx.Client) -> int:
    groups = {}
    url = f"{DOGAPI}/groups"
    while url:
        body = client.get(url).raise_for_status().json()
        for g in body.get("data", []):
            groups[g["id"]] = g["attributes"]["name"]
        url = (body.get("links") or {}).get("next")

    breeds = []
    url = f"{DOGAPI}/breeds?page[size]=1000"
    while url:
        body = client.get(url).raise_for_status().json()
        for b in body.get("data", []):
            attrs = b.get("attributes", {})
            attrs.pop("images", None)       # image URLs are not needed and make the file huge
            group_id = (((b.get("relationships") or {}).get("group") or {}).get("data") or {}).get("id")
            breeds.append({"id": b["id"], "group": groups.get(group_id), **attrs})
        url = (body.get("links") or {}).get("next")
        time.sleep(0.3)

    config.DOGAPI_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "https://dogapi.dog (MIT License)", "breeds": breeds}
    config.DOGAPI_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(breeds)


def main() -> None:
    headers = {"User-Agent": user_agent()}
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
        print("Fetching Wikipedia articles...")
        n_wiki = fetch_wikipedia(client)
        print(f"-> {n_wiki} articles saved to {config.WIKI_DIR}")
        print("Fetching dogapi.dog breeds...")
        n_api = fetch_dogapi(client)
        print(f"-> {n_api} breeds saved to {config.DOGAPI_FILE}")
    if n_wiki == 0 or n_api == 0:
        sys.exit("Fetch failed - see warnings above.")


if __name__ == "__main__":
    main()