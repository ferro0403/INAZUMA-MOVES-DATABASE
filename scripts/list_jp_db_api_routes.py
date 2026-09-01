#!/usr/bin/env python3
import re,urllib.request,urllib.parse
BASE='https://inazuma-eleven-db.vercel.app'
UA='Mozilla/5.0 (compatible; InazumaMovesDatabase/1.0)'
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode('utf-8','replace')
urls=set()
for page in ['/character','/skill','/character/c07070020','/skill/whd00150']:
    try: html=get(BASE+page)
    except Exception as e: print('PAGE_ERR',page,e); continue
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I): urls.add(urllib.parse.urljoin(BASE,src))
print('SCRIPTS',len(urls))
routes=set()
for u in sorted(urls):
    try: js=get(u)
    except Exception as e: print('ERR',u,e); continue
    for m in re.findall(r'["\'](/api/[^"\']+)["\']',js): routes.add(m)
    for m in re.findall(r'/api/[A-Za-z0-9_?=&${}./:-]+',js): routes.add(m)
print('ROUTES')
for r in sorted(routes): print(r)
