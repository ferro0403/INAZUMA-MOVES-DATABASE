#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import html as html_lib
import json
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

JP_DB = "https://inazuma-eleven-db.vercel.app"
ZUKAN_JP = "https://zukan.inazuma.jp/skill/"
ZUKAN_EN = "https://zukan.inazuma.jp/en/skill/"
UA = "Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0; +https://github.com/ferro0403/INAZUMA-MOVES-DATABASE)"
WORKERS = 16
RETRIES = 3


def http_get(url: str, timeout: float = 30.0) -> str:
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(0.4 * (2 ** attempt))
    raise last


def get_json(url: str):
    return json.loads(http_get(url))


def clean_name(inner: str) -> str:
    inner = re.sub(r"<rt\b[^>]*>.*?</rt>", "", inner, flags=re.I | re.S)
    inner = re.sub(r"<[^>]+>", "", inner)
    return re.sub(r"\s+", " ", html_lib.unescape(inner)).strip()


def zukan_names(raw: str) -> list[str]:
    out = []
    for inner in re.findall(r'<span\s+class=["\']name["\'][^>]*>(.*?)</span>', raw, flags=re.I | re.S):
        n = clean_name(inner)
        if n:
            out.append(n)
    return out


def build_english_bridge() -> tuple[dict[str, str], dict]:
    candidates: dict[str, set[str]] = defaultdict(set)
    counts = []
    total_pairs = 0
    # The official catalog currently spans 19 paired JP/EN pages (903 entries).
    for page in range(1, 20):
        jp = zukan_names(http_get(f"{ZUKAN_JP}?page={page}"))
        en = zukan_names(http_get(f"{ZUKAN_EN}?page={page}"))
        counts.append({"page": page, "jp": len(jp), "en": len(en)})
        if len(jp) != len(en):
            raise RuntimeError(f"Official Zukan page {page}: JP/EN count mismatch {len(jp)} != {len(en)}")
        total_pairs += len(jp)
        for j, e in zip(jp, en):
            candidates[j].add(e)
    bridge = {jp: next(iter(names)) for jp, names in candidates.items() if len(names) == 1}
    ambiguous = {jp: sorted(names) for jp, names in candidates.items() if len(names) > 1}
    return bridge, {
        "pages": counts,
        "totalPairedRows": total_pairs,
        "uniqueJapaneseNames": len(candidates),
        "resolvedUniqueNames": len(bridge),
        "ambiguousJapaneseNames": ambiguous,
    }


def norm_type(value: str | None) -> str | None:
    return {
        "シュート技": "shot",
        "オフェンス技": "dribble",
        "ディフェンス技": "defense",
        "キーパー技": "save",
    }.get((value or "").strip())


def norm_element(value: str | None) -> str | None:
    return {"火": "Fire", "林": "Forest", "風": "Wind", "山": "Mountain", "無": "Void"}.get((value or "").strip())


def build_skill_table(bridge: dict[str, str]) -> tuple[dict[str, dict], dict]:
    payload = get_json(f"{JP_DB}/api/get-skills-list")
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError("Unexpected /api/get-skills-list response")
    out = {}
    missing_english = []
    malformed = []
    for row in rows:
        sid = row.get("skill_id")
        if not sid:
            malformed.append(row)
            continue
        jp = (row.get("name") or "").strip() or None
        en = bridge.get(jp) if jp else None
        move = {
            "skillId": sid,
            "name": en,
            "jpName": jp,
            "type": norm_type(row.get("type")),
            "element": norm_element(row.get("element")),
            "power": row.get("power_normal"),
            "tension": row.get("tension_normal"),
            "sourceUrl": f"{JP_DB}/skill/{sid}",
            "englishNameStatus": "official_zukan" if en else "no_official_zukan_entry",
        }
        if not en:
            missing_english.append({"skillId": sid, "jpName": jp})
        out[sid] = move
    return out, {
        "sourceRows": len(rows),
        "resolvedSkills": len(out),
        "missingOfficialEnglish": missing_english,
        "malformedRows": len(malformed),
    }


def parse_character_page(raw: str, expected_no: int) -> list[str]:
    # Verify direct mapping from public No. to the character_id returned by the API.
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_lib.unescape(text)
    m = re.search(r"\bNo\.\s*(\d+)\b", text)
    if not m:
        raise ValueError("public No. not present in character page")
    found = int(m.group(1))
    if found != expected_no:
        raise ValueError(f"public No. mismatch: expected {expected_no}, found {found}")
    ids = []
    for sid in re.findall(r'href=["\']/skill/([A-Za-z0-9_-]+)["\']', raw, flags=re.I):
        if sid not in ids:
            ids.append(sid)
    if not ids:
        for sid in re.findall(r"/skill/([A-Za-z0-9_-]+)", raw):
            if sid not in ids:
                ids.append(sid)
    return ids


def fetch_character_moves(row: dict) -> tuple[int, dict | None, dict | None]:
    no = int(row["inagle_no"])
    cid = row.get("character_id")
    if not cid:
        return no, None, {"playerId": no, "error": "missing character_id"}
    url = f"{JP_DB}/character/{cid}"
    try:
        raw = http_get(url)
        skill_ids = parse_character_page(raw, no)
        return no, {"row": row, "skillIds": skill_ids, "sourceUrl": url}, None
    except Exception as exc:
        return no, None, {"playerId": no, "characterId": cid, "sourceUrl": url, "error": str(exc)}


def main() -> int:
    started = time.time()
    Path("data").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)

    print("[1/4] Fetching direct character list...", flush=True)
    char_payload = get_json(f"{JP_DB}/api/get-characters-list")
    all_rows = char_payload.get("data") if isinstance(char_payload, dict) else char_payload
    if not isinstance(all_rows, list):
        raise RuntimeError("Unexpected /api/get-characters-list response")

    by_no: dict[int, list[dict]] = defaultdict(list)
    rows_without_no = 0
    for row in all_rows:
        try:
            no = int(row.get("inagle_no"))
        except (TypeError, ValueError):
            rows_without_no += 1
            continue
        by_no[no].append(row)

    duplicates = {str(no): [r.get("character_id") for r in rs] for no, rs in by_no.items() if len(rs) != 1}
    unique_rows = [rs[0] for no, rs in sorted(by_no.items()) if len(rs) == 1]
    print(f"Character rows: {len(all_rows)}; unique public Nos: {len(unique_rows)}; duplicate Nos: {len(duplicates)}", flush=True)

    print("[2/4] Building official JP -> EN move-name bridge...", flush=True)
    bridge, bridge_report = build_english_bridge()
    print(f"Official paired rows: {bridge_report['totalPairedRows']}; unique resolved JP names: {bridge_report['resolvedUniqueNames']}", flush=True)

    print("[3/4] Fetching structured skill metadata...", flush=True)
    skills, skill_report = build_skill_table(bridge)
    print(f"Skills: {skill_report['resolvedSkills']}; without official English entry: {len(skill_report['missingOfficialEnglish'])}", flush=True)

    print(f"[4/4] Fetching ownership pages with {WORKERS} workers...", flush=True)
    ownership: dict[int, dict] = {}
    errors = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_character_moves, row) for row in unique_rows]
        for fut in concurrent.futures.as_completed(futures):
            no, result, error = fut.result()
            done += 1
            if result is not None:
                ownership[no] = result
            if error is not None:
                errors.append(error)
            if done % 250 == 0 or done == len(futures):
                print(f"  {done}/{len(futures)} pages; ok={len(ownership)} errors={len(errors)}", flush=True)

    player_db: dict[str, dict] = {}
    unknown_skill_refs = []
    total_links = 0
    players_with_no_moves = []
    for no in sorted(ownership):
        item = ownership[no]
        row = item["row"]
        moves = []
        for sid in item["skillIds"]:
            total_links += 1
            meta = skills.get(sid)
            if meta is None:
                unknown_skill_refs.append({"playerId": no, "skillId": sid})
                moves.append({
                    "skillId": sid, "name": None, "jpName": None, "type": None,
                    "element": None, "power": None, "tension": None,
                    "sourceUrl": f"{JP_DB}/skill/{sid}", "englishNameStatus": "unknown_skill_id",
                })
            else:
                moves.append(meta)
        if not moves:
            players_with_no_moves.append(no)
        player_db[str(no)] = {
            "playerId": no,
            "characterId": row.get("character_id"),
            "jpName": row.get("full_name"),
            "nicknameJa": row.get("nickname"),
            "teamJa": row.get("team"),
            "role": row.get("character_role"),
            "position": row.get("position"),
            "element": norm_element(row.get("element")),
            "sourceUrl": item["sourceUrl"],
            "moves": moves,
        }

    report = {
        "schemaVersion": 1,
        "sources": {
            "characters": f"{JP_DB}/api/get-characters-list",
            "skills": f"{JP_DB}/api/get-skills-list",
            "ownership": f"{JP_DB}/character/<character_id>",
            "officialEnglishNames": [ZUKAN_JP, ZUKAN_EN],
        },
        "sourceCharacterRows": len(all_rows),
        "rowsWithoutPublicNo": rows_without_no,
        "duplicatePublicNos": duplicates,
        "eligibleUniquePublicNos": len(unique_rows),
        "resolvedOwnershipPages": len(ownership),
        "ownershipErrors": errors,
        "playersWithNoMoveLinks": players_with_no_moves,
        "totalPlayerMoveLinks": total_links,
        "unknownSkillReferences": unknown_skill_refs,
        "skills": skill_report,
        "officialEnglishBridge": bridge_report,
        "highIdValidation": {
            "4487": player_db.get("4487"),
            "4507": player_db.get("4507"),
        },
        "timingSeconds": round(time.time() - started, 3),
    }

    Path("data/PLAYER_MOVES_DATABASE.json").write_text(json.dumps(player_db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("data/SKILLS_DATABASE.json").write_text(json.dumps({k: skills[k] for k in sorted(skills)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("reports/full_extraction_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("DONE", json.dumps({
        "players": len(player_db),
        "skills": len(skills),
        "moveLinks": total_links,
        "ownershipErrors": len(errors),
        "unknownSkillRefs": len(unknown_skill_refs),
        "missingOfficialEnglish": len(skill_report["missingOfficialEnglish"]),
        "seconds": report["timingSeconds"],
    }, ensure_ascii=False), flush=True)

    # Hard fail only when the core invariant is broken or extraction is broadly incomplete.
    if "4487" not in player_db or "4507" not in player_db:
        return 3
    if len(errors) > max(20, len(unique_rows) // 100):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
