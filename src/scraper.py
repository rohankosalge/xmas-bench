"""Scrape the most recent NYT Mini crosswords and save them as .puz files.

Auth: set NYT_S (preferred) or NYT_USERNAME/NYT_PASSWORD in a .env file.
Run:  python scraper.py [--num N]
"""

import argparse
import datetime
import json
import os
import sys

import puz
import requests
from dotenv import load_dotenv

import config

ORACLE_URL = "https://www.nytimes.com/svc/crosswords/v2/oracle/mini.json"
PUZZLE_URL = "https://www.nytimes.com/svc/crosswords/v6/puzzle/mini/{}.json"
LOGIN_URL = "https://myaccount.nytimes.com/svc/ios/v2/login"


def resolve_token():
    """Return an NYT-S token from env, logging in with user/pass if needed."""
    token = os.getenv("NYT_S")
    if token:
        return token

    username = os.getenv("NYT_USERNAME")
    password = os.getenv("NYT_PASSWORD")
    if not (username and password):
        sys.exit(
            "No credentials found. Set NYT_S (preferred) or "
            "NYT_USERNAME/NYT_PASSWORD in .env (see README)."
        )

    res = requests.post(
        LOGIN_URL,
        data={"login": username, "password": password},
        headers={
            "User-Agent": "Crossword/1844.220922 CFNetwork/1335.0.3 Darwin/21.6.0",
            "client_id": "ios.crosswords",
        },
    )
    if not res.ok:
        sys.exit(
            "NYT login failed (this can happen due to anti-automation). "
            "Grab your NYT-S cookie manually instead — see README."
        )
    for cookie in res.json()["data"]["cookies"]:
        if cookie["name"] == "NYT-S":
            return cookie["cipheredValue"]
    sys.exit("Login succeeded but no NYT-S cookie was returned.")


def latest_mini_date():
    res = requests.get(ORACLE_URL)
    res.raise_for_status()
    return datetime.date.fromisoformat(res.json()["results"]["current"]["print_date"])


def to_puz(data):
    """Convert NYT v6 puzzle JSON into a puz.Puzzle (mini => no rebus/markup)."""
    body = data["body"][0]
    puzzle = puz.Puzzle()
    puzzle.author = " and ".join(data.get("constructors", [])).strip()
    puzzle.copyright = data.get("copyright", "")
    puzzle.height = int(body["dimensions"]["height"])
    puzzle.width = int(body["dimensions"]["width"])
    puzzle.title = data.get("title") or data["publicationDate"]

    solution = fill = ""
    for cell in body["cells"]:
        if not cell:
            solution += "."
            fill += "."
        else:
            solution += cell["answer"][0]
            fill += "-"
    puzzle.solution = solution
    puzzle.fill = fill

    clues = sorted(body["clues"], key=lambda c: (int(c["label"]), c["direction"]))
    puzzle.clues = [c["text"][0].get("plain") or "" for c in clues]
    return puzzle


def fetch(date, token):
    res = requests.get(PUZZLE_URL.format(date.isoformat()), cookies={"NYT-S": token})
    if res.status_code == 403:
        sys.exit("Auth rejected (403). Your NYT-S token is missing/expired — see README.")
    if res.status_code == 404:
        return None
    res.raise_for_status()
    return res.json()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=config.NUM_CROSSWORDS)
    num = parser.parse_args().num

    token = resolve_token()
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    date = latest_mini_date()
    saved = puz_count = json_count = 0
    while saved < num:
        data = fetch(date, token)
        if data:
            stem = os.path.join(config.OUTPUT_DIR, f"mini-{date.isoformat()}")
            try:
                to_puz(data).save(f"{stem}.puz")
                puz_count += 1
            except Exception as e:  # not .puz-compatible: fall back to raw JSON
                with open(f"{stem}.json", "w") as f:
                    json.dump(data, f)
                json_count += 1
                print(f"  {date}: saved JSON instead of .puz ({e})")
            saved += 1
        date -= datetime.timedelta(days=1)

    print(f"Saved {saved} puzzles: {puz_count} .puz, {json_count} json -> {config.OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
