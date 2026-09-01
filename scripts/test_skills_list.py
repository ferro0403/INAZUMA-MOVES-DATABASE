#!/usr/bin/env python3
import json,urllib.request
BASE='https://inazuma-eleven-db.vercel.app'
req=urllib.request.Request(BASE+'/api/get-skills-list',headers={'User-Agent':'Mozilla/5.0 (InazumaMovesDatabase)'})
with urllib.request.urlopen(req,timeout=30) as r: p=json.load(r)
data=p.get('data') if isinstance(p,dict) else p
print('COUNT',len(data) if isinstance(data,list) else None)
print('KEYS',sorted(data[0].keys()) if isinstance(data,list) and data else [])
for target in ['whd00150','rhk10010','whs00030']:
    ms=[]
    for x in data or []:
        if any(str(x.get(k))==target for k in ['skill_id','id','skillId','waza_id','internal_code']): ms.append(x)
    print('\nTARGET',target,'MATCHES',len(ms))
    for x in ms[:3]: print(json.dumps(x,ensure_ascii=False,sort_keys=True))
