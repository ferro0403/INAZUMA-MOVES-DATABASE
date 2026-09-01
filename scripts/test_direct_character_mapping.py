#!/usr/bin/env python3
import json,urllib.request
BASE='https://inazuma-eleven-db.vercel.app'
UA='Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0)'
req=urllib.request.Request(BASE+'/api/get-characters-list',headers={'User-Agent':UA,'Accept':'application/json'})
with urllib.request.urlopen(req,timeout=30) as r:
    payload=json.load(r)
data=payload.get('data') if isinstance(payload,dict) else payload
print('TYPE',type(data).__name__,'COUNT',len(data) if isinstance(data,list) else None)
if not isinstance(data,list):
    print(json.dumps(payload,ensure_ascii=False)[:4000]); raise SystemExit(1)
print('KEYS',sorted(data[0].keys()) if data else [])
for target in [1,38,53,4487,4507,4976]:
    matches=[x for x in data if str(x.get('inagle_no'))==str(target) or str(x.get('no'))==str(target) or str(x.get('id'))==str(target)]
    print('\nTARGET',target,'MATCHES',len(matches))
    for x in matches[:5]:
        print(json.dumps(x,ensure_ascii=False,sort_keys=True))
# Show nearby high IDs to make ordering/schema obvious.
nums=[]
for x in data:
    v=x.get('inagle_no')
    try: n=int(v)
    except: continue
    if 4478<=n<=4515: nums.append(x)
print('\nHIGH_WINDOW_COUNT',len(nums))
for x in nums:
    print(json.dumps(x,ensure_ascii=False,sort_keys=True))
