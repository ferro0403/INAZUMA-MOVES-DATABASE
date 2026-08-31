#!/usr/bin/env python3
import json
import extract_sample_occult as base
q = "query($q: String) { characters(q: $q, limit: 20) { id internalCode name { fr en ja } variants { charaParamId position element rarity image } } }"
for name in ["Nathan Jones", "David Samford", "Neil Turner", "Mark Evans"]:
    print("QUERY", name)
    print(json.dumps(base.graphql(q, {"q": name}), ensure_ascii=False, indent=2))
