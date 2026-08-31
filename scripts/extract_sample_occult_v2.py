#!/usr/bin/env python3
"""V2 runner: fix source H1 selection without duplicating the extractor."""

import re
import sys

import extract_sample_occult as base


def extract_content_h1(raw: str) -> str | None:
    # Next.js renders the site logo as the first <h1> ("イナイレDB") and the actual
    # character/skill title later. Select the last meaningful H1, never the site header.
    matches = re.findall(r"<h1\b[^>]*>(.*?)</h1>", raw, flags=re.I | re.S)
    for inner in reversed(matches):
        text = base.strip_tags(inner).strip()
        if text and text != "イナイレDB":
            return text
    return None


base.extract_h1 = extract_content_h1

if __name__ == "__main__":
    sys.exit(base.main())
