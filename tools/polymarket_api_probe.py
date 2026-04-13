import json
import sys
import urllib.error
import urllib.request


URLS = [
    ("trades", "https://data-api.polymarket.com/trades?limit=1"),
    (
        "positions",
        "https://data-api.polymarket.com/positions?user=0x0000000000000000000000000000000000000000&sizeThreshold=.1",
    ),
]


def fetch(name: str, url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "polymarket-bot-local-probe/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            sample = response.read(200).decode("utf-8", "replace")
            return {"name": name, "status": response.status, "sample": sample}
    except urllib.error.HTTPError as exc:
        sample = exc.read(200).decode("utf-8", "replace")
        return {"name": name, "status": exc.code, "sample": sample, "error": "http_error"}


def main() -> int:
    results = [fetch(name, url) for name, url in URLS]
    print(json.dumps(results, ensure_ascii=True, indent=2))
    bad = [item for item in results if item["status"] != 200]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
