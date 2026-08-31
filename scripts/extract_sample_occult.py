#!/usr/bin/env python3
"""Extract a validated IE1 Occult sample from the Japanese VR DB.

This script deliberately does not touch the game repository. It validates the public
No. against the expected stable playerId, reads every source-owned learned skill from
the Japanese character page, and enriches each skill through Azalee's public GraphQL
mirror (EN/JA names, category, element, power, tension).
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

JP_DB = "https://inazuma-eleven-db.vercel.app"
AZALEE_GRAPHQL = "https://azalee.rosegriffon.fr/api/graphql"

# Stable game IDs 38..53 are the public Zukan/Japanese-DB No. values for the IE1
# Occult variants. Internal codes are independently cross-checked against the source page No.
PLAYERS = [
    (38, "Nathan Jones", "c01000410"),
    (39, "Russell Walk", "c01000420"),
    (40, "Jason Jones", "c01000430"),
    (41, "Ken Furan", "c01000440"),
    (42, "Jerry Fulton", "c01000450"),
    (43, "Ray Mannings", "c01000460"),
    (44, "Robert Mayer", "c01000470"),
    (45, "Alexander Brave", "c01000480"),
    (46, "Johan Tassman", "c01000490"),
    (47, "Troy Moon", "c01000500"),
    (48, "Burt Wolf", "c01000510"),
    (49, "Rob Crombie", "c01000520"),
    (50, "Chuck Dollman", "c01000530"),
    (51, "Uxley Allen", "c01000540"),
    (52, "Phil Noir", "c01000550"),
    (53, "Mick Askley", "c01000560"),
]

UA = "Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0; +https://github.com/ferro0403/INAZUMA-MOVES-DATABASE)"


def http_get(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def graphql(query: str, variables: dict, timeout: float = 20.0) -> dict:
    body = json.dumps({"query": query, "variables": variables}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        AZALEE_GRAPHQL,
        data=body,
        method="POST",
        headers={"User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload.get("data") or {}


def strip_tags(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_h1(raw: str) -> str | None:
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", raw, flags=re.I | re.S)
    return strip_tags(m.group(1)) if m else None


def parse_character_page(raw: str, expected_no: int) -> tuple[str | None, list[str]]:
    text = strip_tags(raw)
    no_match = re.search(r"\bNo\.\s*(\d+)\b", text)
    if not no_match:
        raise ValueError("public No. not found in character page")
    found_no = int(no_match.group(1))
    if found_no != expected_no:
        raise ValueError(f"public No. mismatch: expected {expected_no}, found {found_no}")

    # Every learned move shown in the source page is linked to /skill/<stable-id>.
    ids: list[str] = []
    for skill_id in re.findall(r'href=["\']/skill/([A-Za-z0-9_-]+)["\']', raw, flags=re.I):
        if skill_id not in ids:
            ids.append(skill_id)
    if not ids:
        # Next.js may escape slashes inside serialized server data.
        for skill_id in re.findall(r"/skill/([A-Za-z0-9_-]+)", raw):
            if skill_id not in ids:
                ids.append(skill_id)
    return extract_h1(raw), ids


def parse_skill_page(raw: str) -> dict:
    jp_name = extract_h1(raw)
    text = strip_tags(raw)
    category = next((x for x in ("シュート技", "オフェンス技", "ディフェンス技", "キーパー技") if x in text), None)
    element = next((x for x in ("火", "林", "風", "山", "無") if re.search(rf"(?:属性|エレメント)?\s*{re.escape(x)}", text)), None)
    # Source pages render values as e.g. 60T / 威力60. These are fallback values only;
    # Azalee metadata wins when exact JP-name resolution succeeds.
    tension = None
    power = None
    mt = re.search(r"(\d+)\s*T", text)
    mp = re.search(r"威力\s*(\d+)", text)
    if mt:
        tension = int(mt.group(1))
    if mp:
        power = int(mp.group(1))
    return {"jpName": jp_name, "sourceCategoryJa": category, "sourceElementJa": element, "sourcePower": power, "sourceTension": tension}


def normalize_type(category: str | None) -> str | None:
    c = (category or "").strip().lower()
    mapping = {
        "shoot": "shot", "shot": "shot", "シュート技": "shot",
        "offense": "dribble", "offence": "dribble", "オフェンス技": "dribble",
        "defense": "defense", "defence": "defense", "ディフェンス技": "defense",
        "keep": "save", "keeper": "save", "キーパー技": "save",
    }
    return mapping.get(c)


def normalize_element(element: str | None) -> str | None:
    e = (element or "").strip()
    mapping = {
        "Fire": "Fire", "Forest": "Forest", "Wind": "Wind", "Mountain": "Mountain", "Void": "Void",
        "火": "Fire", "林": "Forest", "風": "Wind", "山": "Mountain", "無": "Void",
    }
    return mapping.get(e)


def azalee_skill_exact(jp_name: str | None) -> tuple[dict | None, str]:
    if not jp_name:
        return None, "missing_jp_name"
    q = "query($q: String) { skills(q: $q, limit: 20) { id name { fr en ja } category element power tension image } }"
    data = graphql(q, {"q": jp_name})
    rows = data.get("skills") or []
    exact = [r for r in rows if ((r.get("name") or {}).get("ja") or "").strip() == jp_name.strip()]
    if len(exact) == 1:
        return exact[0], "exact_jp"
    if len(exact) > 1:
        return None, "ambiguous_exact_jp"
    return None, "not_found_exact_jp"


def main() -> int:
    out: dict[str, dict] = {}
    report = {
        "schemaVersion": 1,
        "source": {"ownership": JP_DB, "metadata": "https://azalee.rosegriffon.fr"},
        "requestedPlayers": len(PLAYERS),
        "resolvedPlayers": 0,
        "unresolvedPlayers": [],
        "resolvedMoves": 0,
        "unresolvedMoves": [],
        "timingSeconds": None,
    }
    skill_cache: dict[str, dict] = {}
    start = time.time()

    for player_id, english_name, internal_code in PLAYERS:
        url = f"{JP_DB}/character/{internal_code}"
        try:
            raw = http_get(url)
            jp_player_name, skill_ids = parse_character_page(raw, player_id)
            if not skill_ids:
                raise ValueError("no learned skill links found")
        except Exception as exc:
            report["unresolvedPlayers"].append({"playerId": str(player_id), "name": english_name, "internalCode": internal_code, "error": str(exc)})
            continue

        moves = []
        for skill_id in skill_ids:
            if skill_id in skill_cache:
                move = dict(skill_cache[skill_id])
            else:
                skill_url = f"{JP_DB}/skill/{skill_id}"
                try:
                    sraw = http_get(skill_url)
                    src = parse_skill_page(sraw)
                    meta, resolution = azalee_skill_exact(src.get("jpName"))
                    names = (meta or {}).get("name") or {}
                    move = {
                        "skillId": skill_id,
                        "name": names.get("en") if meta else None,
                        "jpName": (names.get("ja") if meta else None) or src.get("jpName"),
                        "type": normalize_type((meta or {}).get("category")) or normalize_type(src.get("sourceCategoryJa")),
                        "element": normalize_element((meta or {}).get("element")) or normalize_element(src.get("sourceElementJa")),
                        "power": (meta or {}).get("power") if meta and (meta or {}).get("power") is not None else src.get("sourcePower"),
                        "tension": (meta or {}).get("tension") if meta and (meta or {}).get("tension") is not None else src.get("sourceTension"),
                        "sourceUrl": skill_url,
                        "metadataResolution": resolution,
                    }
                    skill_cache[skill_id] = dict(move)
                except Exception as exc:
                    move = {
                        "skillId": skill_id, "name": None, "jpName": None, "type": None, "element": None,
                        "power": None, "tension": None, "sourceUrl": skill_url, "metadataResolution": "error",
                    }
                    report["unresolvedMoves"].append({"playerId": str(player_id), "skillId": skill_id, "error": str(exc)})
            moves.append(move)
            if move.get("name") and move.get("type") and move.get("element") and move.get("power") is not None and move.get("tension") is not None:
                report["resolvedMoves"] += 1
            elif not any(x.get("playerId") == str(player_id) and x.get("skillId") == skill_id for x in report["unresolvedMoves"]):
                report["unresolvedMoves"].append({"playerId": str(player_id), "skillId": skill_id, "error": "incomplete metadata", "metadataResolution": move.get("metadataResolution")})

        out[str(player_id)] = {
            "name": english_name,
            "jpName": jp_player_name,
            "sourceNo": player_id,
            "internalCode": internal_code,
            "sourceUrl": url,
            "moves": moves,
        }
        report["resolvedPlayers"] += 1
        print(f"{player_id}: {english_name}: {len(moves)} moves", flush=True)

    report["timingSeconds"] = round(time.time() - start, 3)
    report["totalMoveLinks"] = sum(len(p["moves"]) for p in out.values())

    Path("data").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    Path("data/sample_ie1_occult_player_moves.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("reports/sample_ie1_occult_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # A sample with no resolved players is a hard failure. Partial resolution remains visible
    # in the report and is intentionally not guessed.
    return 0 if report["resolvedPlayers"] else 2


if __name__ == "__main__":
    sys.exit(main())
