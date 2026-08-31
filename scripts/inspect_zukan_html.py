#!/usr/bin/env python3
import urllib.request

UA = "Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0)"
for url, needle in [
    ("https://zukan.inazuma.jp/skill/?page=1", "怨霊"),
    ("https://zukan.inazuma.jp/en/skill/?page=1", "Ghost Pull"),
]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    i = raw.find(needle)
    print("URL", url, "LEN", len(raw), "INDEX", i)
    print(raw[max(0, i-1000):i+1400])
    print("\n---END---\n")
