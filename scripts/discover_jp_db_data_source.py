#!/usr/bin/env python3
import json,re,urllib.request,urllib.parse
BASE='https://inazuma-eleven-db.vercel.app'
UA='Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0)'

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode('utf-8','replace')

html=get(BASE+'/character')
print('CHARACTER_HTML_LEN',len(html))
# direct clues in initial HTML
for pat in ['supabase','api/','character','chara','No.','_next/data','__next_f.push','postgres','graphql']:
    if pat.lower() in html.lower(): print('HTML_HAS',pat)

scripts=[]
for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I):
    url=urllib.parse.urljoin(BASE,src)
    if url not in scripts: scripts.append(url)
print('SCRIPT_COUNT',len(scripts))

needles=['supabase','graphql','/api/','character','chara','skill','fetch(','axios','rpc(','from("','from(\'']
for i,url in enumerate(scripts):
    try:
        js=get(url)
    except Exception as e:
        print('SCRIPT_ERR',url,repr(e)); continue
    hits=[]
    low=js.lower()
    for n in needles:
        if n.lower() in low: hits.append(n)
    if hits:
        print('\nSCRIPT',i,url,'LEN',len(js),'HITS',hits)
        # Print compact context around likely data/API clues.
        for needle in ['supabase','/api/','graphql','characters','characterlist','charalist','chara_param','charaParam','skill']:
            p=low.find(needle.lower())
            if p>=0:
                print('CTX',needle,js[max(0,p-350):p+1000].replace('\n',' ')[:1350])

# also inspect RSC links / hrefs that look data-like
urls=sorted(set(re.findall(r'https?://[^"\'<>\\ ]+',html)))
print('\nABS_URLS',len(urls))
for u in urls:
    if any(k in u.lower() for k in ['supabase','api','json','vercel']): print('URL',u[:500])
