#!/usr/bin/env python3
import asyncio, json, os, re, time
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

BINTV_HOME = os.getenv('BINTV_HOME', 'https://www.bintv.cc/')
PORT = int(os.getenv('PORT', '8787'))
TIMEOUT = float(os.getenv('BINTV_TIMEOUT', '20'))

app = FastAPI(title='Reel Live TV API', version='1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

BASE_DIR=os.path.dirname(os.path.abspath(__file__))

@app.get('/')
async def reel_home():
    return FileResponse(os.path.join(BASE_DIR, 'Reel.html'), media_type='text/html')

@app.get('/Reel.html')
async def reel_html():
    return FileResponse(os.path.join(BASE_DIR, 'Reel.html'), media_type='text/html')

SPORTS = [
    ('american football','american football'),('australian rules','australian rules'),
    ('formula 1','motorsport'),('formula one','motorsport'),('motogp','motorsport'),
    ('ice hockey','hockey'),('table tennis','table tennis'),('mixed martial arts','mma'),
    ('football','football'),('soccer','football'),('basketball','basketball'),
    ('tennis','tennis'),('cricket','cricket'),('baseball','baseball'),('hockey','hockey'),
    ('rugby league','rugby league'),('rugby','rugby'),('motorsport','motorsport'),
    ('boxing','boxing'),('mma','mma'),('ufc','mma'),('golf','golf'),('volleyball','volleyball'),
    ('wrestling','wrestling'),('wwe','wrestling'),('darts','darts'),('snooker','snooker'),
    ('esports','esports'),('cycling','cycling'),('handball','handball'),('badminton','badminton'),
]

def sport_from_text(text):
    t = (text or '').lower()
    for needle, sport in SPORTS:
        if needle in t:
            return sport
    return ''

def normalize_url(raw, base=BINTV_HOME):
    if not raw: return ''
    s = str(raw).strip().replace('&amp;', '&')
    for _ in range(3):
        try:
            u = urlparse(s)
            if not u.scheme:
                s = urljoin(base, s); continue
            q = parse_qs(u.query)
            wrapped = q.get('src', q.get('url', q.get('embed', [])))
            if wrapped:
                s = wrapped[0]
                continue
            return s.split('#',1)[0]
        except Exception:
            return ''
    return ''

def playable(u):
    try:
        p=urlparse(u)
        h=p.hostname or ''
        return h.endswith('embedindia.st') or h.endswith('bintv.cc') or h.endswith('bintv-nett.blogspot.com')
    except Exception:
        return False

def title_from_context(text, url):
    t = re.sub(r'\s+', ' ', text or '').strip()
    if t and len(t) < 180:
        return t
    try:
        p=urlparse(url)
        q=parse_qs(p.query)
        if q.get('title'): return q['title'][0]
        m=re.search(r'/embed/[^/]+/([^/?#]+)', url, re.I)
        if m: return re.sub(r'[-_]+',' ',m.group(1)).strip().title()
    except Exception: pass
    return 'Live sport'

def extract_from_html(html):
    soup=BeautifulSoup(html,'html.parser')
    games=[]; seen=set()

    def add(raw, title='', sport=''):
        u=normalize_url(raw)
        if not u or not playable(u) or u in seen: return
        seen.add(u)
        final_title=title_from_context(title,u)
        games.append({'title':final_title,'url':u,'sport':sport or sport_from_text(final_title+ ' '+u),'status':'live'})

    # Standard links and common data attributes.
    for tag in soup.find_all(True):
        attrs=tag.attrs or {}
        context=tag.get_text(' ', strip=True)
        for key in ('href','src','data-href','data-url','data-src','data-link','data-stream','data-embed'):
            val=attrs.get(key)
            if isinstance(val, list): val=' '.join(val)
            if val: add(val, context)
        # React/Next data blobs frequently contain JSON strings with URLs.
        for key,val in attrs.items():
            if isinstance(val,str) and ('http' in val or 'embedindia' in val or 'bintv' in val):
                for m in re.findall(r'https?[^\s"\'<>]+', val): add(m, context)

    # Raw HTML / script state: collect URLs and nearby labels.
    raw=str(soup)
    for m in re.finditer(r'https?[^\s"\'<>\\]+', raw):
        raw_url=m.group(0).rstrip('),]}')
        add(raw_url, raw[max(0,m.start()-180):m.start()])

    # JSON-LD / embedded state text.
    for script in soup.find_all('script'):
        text=script.string or script.get_text() or ''
        for m in re.finditer(r'https?[^\s"\'<>\\]+', text):
            add(m.group(0).rstrip('),]}'), '')

    # Keep likely event/provider links and discard obvious site chrome.
    cleaned=[]
    for g in games:
        u=g['url']
        if 'bintv.cc' in (urlparse(u).hostname or ''):
            path=urlparse(u).path.lower()
            if path in ('','/','/about','/contact','/privacy','/terms'): continue
            if not any(x in (path+'?'+urlparse(u).query) for x in ('event','match','game','live','watch','sports','sport','fixture','channel')) and path.count('/') < 2:
                continue
        cleaned.append(g)
    return cleaned


def fetch_http():
    headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36','Accept':'text/html,application/xhtml+xml'}
    r=requests.get(BINTV_HOME,headers=headers,timeout=TIMEOUT)
    r.raise_for_status()
    return r.text, 'requests'

async def fetch_browser():
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return None, 'playwright-not-installed'
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            page=await browser.new_page(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36')
            await page.goto(BINTV_HOME, wait_until='domcontentloaded', timeout=int(TIMEOUT*1000))
            await page.wait_for_timeout(2500)
            html=await page.content()
            await browser.close()
            return html, 'playwright'
    except Exception as e:
        return None, f'playwright-error:{type(e).__name__}'

cache={'games':[], 'fetchedAt':None, 'source':None, 'error':None}

async def discover():
    global cache
    errors=[]
    try:
        html,src=fetch_http()
        games=extract_from_html(html)
        if games:
            cache={'games':games,'fetchedAt':datetime.now(timezone.utc).isoformat(),'source':src,'error':None}
            return cache
        errors.append('HTTP page contained no event links')
    except Exception as e: errors.append('HTTP '+str(e))

    html,src=await fetch_browser()
    if html:
        games=extract_from_html(html)
        if games:
            cache={'games':games,'fetchedAt':datetime.now(timezone.utc).isoformat(),'source':src,'error':None}
            return cache
    errors.append(src)
    cache={'games':cache.get('games',[]),'fetchedAt':cache.get('fetchedAt'),'source':cache.get('source'),'error':'; '.join(errors)}
    return cache

@app.get('/api/health')
async def health():
    return {'ok':True,'service':'reel-live-tv-api','time':datetime.now(timezone.utc).isoformat()}

@app.get('/api/live-games')
async def live_games(refresh: int=0):
    # 2-minute cache unless explicitly refreshed.
    fresh=False
    if cache.get('fetchedAt'):
        try:
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(cache['fetchedAt'])).total_seconds()
            fresh=age < 120
        except Exception: pass
    if refresh or not fresh:
        await discover()
    return {'ok':True,'source':cache.get('source'),'fetchedAt':cache.get('fetchedAt'),'error':cache.get('error'),'games':cache.get('games',[])}

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=PORT)
