#!/usr/bin/env python3
import re
import urllib.parse
import urllib.request

BASE = "https://zukan.inazuma.jp"
SEARCH = BASE + "/en/chara_list/process_form"
UA = "Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0)"

def post(params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(SEARCH, data=data, method="POST", headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")

def strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()

def find_target(no):
    for page in range(1, 30):
        params = {"rc":"0", "per_page":"200", "page":str(page)}
        raw = post(params)
        for tb in re.findall(r"<tbody\b[^>]*>(.*?)</tbody>", raw, re.I|re.S):
            cells = re.findall(r"<td\b[^>]*>(.*?)</td>", tb, re.I|re.S)
            if len(cells) < 2:
                continue
            txt = strip(cells[1])
            if txt == str(no):
                hrefs = re.findall(r'href=["\']([^"\']+)["\']', tb, re.I)
                href = next((h for h in hrefs if "chara_param" in h), hrefs[0] if hrefs else None)
                return page, href, tb
    return None, None, None

for no in [38, 4507, 4487]:
    page, href, tb = find_target(no)
    print("TARGET", no, "PAGE", page, "HREF", href)
    if not href:
        continue
    url = href if href.startswith("http") else BASE + href
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    codes = sorted(set(re.findall(r"c\d{8,}", raw, re.I)))
    print("DETAIL", url, "LEN", len(raw), "CODES", codes[:30], "COUNT", len(codes))
    for needle in ["c01000410", "internal", "chara", "4487", "4507"]:
        i = raw.lower().find(needle.lower())
        if i >= 0:
            print("NEEDLE", needle, raw[max(0,i-300):i+700])
            break
