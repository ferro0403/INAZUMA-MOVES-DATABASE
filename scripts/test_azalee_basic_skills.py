#!/usr/bin/env python3
import json,urllib.request
URL='https://azalee.rosegriffon.fr/api/graphql'
Q='query($q: String) { skills(q: $q, limit: 20) { id name { fr en ja } category element power tension image } }'
for q in ['rhk10010','きあいのパンチ','rhd10020','ショルダーチャージ']:
    body=json.dumps({'query':Q,'variables':{'q':q}},ensure_ascii=False).encode()
    req=urllib.request.Request(URL,data=body,method='POST',headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0 InazumaMovesDatabase'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:p=json.load(r)
        print('\nQUERY',q)
        print(json.dumps(p,ensure_ascii=False,sort_keys=True))
    except Exception as e: print('ERR',q,repr(e))
