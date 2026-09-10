"""Build additive, dependency-free pages for the existing grmove.com site."""
import hashlib, html, json, re, secrets
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
HOST='https://grmove.com'
guides=json.loads((ROOT/'content/guides.json').read_text())
articles=json.loads((ROOT/'content/articles.json').read_text())
series=json.loads((ROOT/'content/series.json').read_text())
esc=html.escape

BRAND_SOURCE=(ROOT/'baseline/index.html').read_text()
BRAND_CSS=re.search(r'<style>(.*?)</style>',BRAND_SOURCE,re.S).group(1)
BRAND_NAV=re.search(r'<nav\b.*?</nav>',BRAND_SOURCE,re.S).group()
BRAND_NAV=BRAND_NAV.replace('href="#"','href="/"').replace('href="#','href="/#')
BRAND_FOOTER=re.search(r'<footer\b.*?</footer>',BRAND_SOURCE,re.S).group()
RESOURCE_LINKS='<div><a href="/guides/">Practical guides</a></div><div><a href="/articles/">Articles</a></div>'
BRAND_FOOTER=BRAND_FOOTER.replace('<div class="contact">','<div class="contact">'+RESOURCE_LINKS,1)
# Photograph credits belong to the homepage, which retains those photographs.
BRAND_FOOTER=re.sub(r'<div class="photo-credit">.*?</div>','',BRAND_FOOTER,flags=re.S)
CSS=BRAND_CSS+"""
a:focus-visible,summary:focus-visible{outline:3px solid var(--gold);outline-offset:5px}
.wrap{width:min(1160px,calc(100% - 42px));margin:0 auto}
.intro{padding:64px 0 38px;max-width:930px}
.intro .eyebrow,.card .eyebrow{color:#876913}
.intro h1{font-size:clamp(2.5rem,5vw,4.7rem);line-height:1.02}
.intro .answer{padding:0;border:0;background:none;font-size:1.17rem;color:#52606a}
.byline{font-size:.9rem;color:var(--muted)}
.body-grid{display:grid;grid-template-columns:minmax(0,760px) 250px;gap:50px;align-items:start}
article section{padding:30px 0;border-top:1px solid var(--line)}
article h2{font-size:clamp(1.7rem,3vw,2.4rem)}
article p{margin:0 0 18px}article li{margin-bottom:12px}
aside{background:var(--paper);padding:25px;border-radius:22px;position:sticky;top:100px}
aside h2{font-size:1.2rem}aside a{display:block;margin-bottom:14px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin:12px 0 64px}
.card{background:var(--paper);padding:26px;border:1px solid var(--line);border-radius:22px}
.card h2{font-size:1.65rem}.card h2 a{text-decoration:none}.card h2 a:hover{text-decoration:underline}
details{padding:18px 0;border-bottom:1px solid var(--line)}summary{font-weight:700;cursor:pointer}details p{padding-top:16px}
article .cta{padding:30px;border-radius:22px;margin:24px 0 64px}article .cta p{color:#c6d0d6}
.publisher-note{color:var(--muted);font-size:.9rem;margin:0 0 36px}
.skip{position:absolute;left:-9999px}.skip:focus{left:15px;top:10px;background:white;padding:10px;z-index:30}
@media(max-width:900px){.body-grid{grid-template-columns:1fr;gap:20px}aside{position:static;margin-bottom:35px}.nav-inner{gap:12px}.intro{padding-top:40px}}
@media(max-width:600px){.cards{grid-template-columns:1fr}.wrap{width:calc(100% - 28px)}.nav-inner{height:auto;min-height:76px;flex-wrap:wrap;padding:12px 0}.nav-links{margin-left:auto}.intro h1{font-size:2.6rem}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

def write(path,text):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)

def card(g,collection='guides'):
    return f'<div class="card"><span class="eyebrow">{esc(g["audience"])}</span><h2><a href="/{collection}/{g["slug"]}/">{esc(g["title"])}</a></h2><p>{esc(g["description"])}</p></div>'

def sections_html(item):
    parts=[]
    for sec in item['sections']:
        value='<section><h2>'+esc(sec['heading'])+'</h2>'
        value+=''.join('<p>'+esc(p)+'</p>' for p in sec.get('paragraphs',[]))
        if sec.get('items'):value+='<ul>'+''.join('<li>'+esc(t)+'</li>' for t in sec['items'])+'</ul>'
        if sec.get('references'):
            value+='<p class="byline">Sources: '+', '.join('<a href="'+esc(r['url'],quote=True)+'">'+esc(r['title'])+'</a>' for r in sec['references'])+'</p>'
        parts.append(value+'</section>')
    return ''.join(parts)

def shell(title,description,path,body,article=False):
    url=HOST+path
    graph=[{'@type':'Organization','@id':HOST+'/#organization','name':'Good Remedy','url':HOST+'/'},
           {'@type':'Article' if article else 'CollectionPage','@id':url+'#page','url':url,
            'headline':title,'description':description,'inLanguage':'en-US',
            'publisher':{'@id':HOST+'/#organization'},'author':{'@id':HOST+'/#organization'}}]
    data=json.dumps({'@context':'https://schema.org','@graph':graph}).replace('<','\\u003c')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} | Good Remedy</title><meta name="description" content="{esc(description,quote=True)}"><link rel="canonical" href="{url}"><meta property="og:title" content="{esc(title,quote=True)}"><meta property="og:description" content="{esc(description,quote=True)}"><meta property="og:url" content="{url}"><meta property="og:type" content="{'article' if article else 'website'}"><meta name="theme-color" content="#071521"><style>{CSS}</style><script type="application/ld+json">{data}</script></head><body><a class="skip" href="#main">Skip to content</a>{BRAND_NAV}<main id="main" class="wrap">{body}<p class="publisher-note">Published by Good Remedy. Examples are illustrative unless explicitly identified otherwise.</p></main>{BRAND_FOOTER}</body></html>'''

keyfile=ROOT/'operations/indexnow-key.txt'
if not keyfile.exists():keyfile.write_text(secrets.token_hex(16))
key=keyfile.read_text().strip()
assert re.fullmatch('[a-f0-9]{32}',key)
write(key+'.txt',key)
write('guides/index.html',shell('AI implementation and operations: practical guides','Explore connected AI operations, implementation partnerships, onboarding, sales research and workflow repair.','/guides/',
      '<div class="intro"><span class="eyebrow">Good Remedy / Practical guides</span><h1>Make the whole operation work.</h1><p class="answer">Start with the job your people need to complete. These guides show what belongs around the AI: the systems, sources, decisions and handoffs that make the work usable.</p><p class="byline">Published by Good Remedy · Implementation and operating guidance</p></div><div class="cards">'+''.join(card(g) for g in guides)+'</div><h2>Ideas about AI and work</h2><div class="cards">'+''.join(card(a,'articles') for a in articles)+'</div>'))
write('articles/index.html',shell(series['title'],series['description'],'/articles/',
      '<div class="intro"><span class="eyebrow">Good Remedy / AI explained</span><h1>'+esc(series['title'])+'</h1><p class="answer">'+esc(series['intro'])+'</p><p class="byline">Published by Good Remedy · A six-part series</p></div><div class="cards">'+''.join(card(a,'articles') for a in articles)+'</div><p>Working through an implementation? <a href="/guides/">Explore the practical guides.</a></p>'))
queries=[]
for i,g in enumerate(guides):
    sections=sections_html(g)
    faq='<section><h2>Common implementation questions</h2>'+''.join('<details><summary>'+esc(q)+'</summary><p>'+esc(a)+'</p></details>' for q,a in g['questions'])+'</section>'
    route='/guides/'+g['slug']+'/'
    cta='mailto:hello@grmove.com?subject='+quote('GR guide: '+g['title'])+'&body='+quote('I read '+HOST+route+'\n\nThe operation we want to improve:\n\nCurrent systems:\n\nWhere we need help:\n')
    related=''.join('<a href="/guides/'+x['slug']+'/">'+esc(x['title'])+'</a>' for x in guides if x!=g)
    related+='<h2>Read further</h2>'+''.join('<a href="/articles/'+a['slug']+'/">'+esc(a['title'])+'</a>' for a in articles if g['slug'] in a['related_guides'])
    body='<div class="intro"><span class="eyebrow">'+esc(g['audience'])+'</span><h1>'+esc(g['title'])+'</h1><p class="answer">'+esc(g['answer'])+'</p><p class="byline">Published by Good Remedy · Practical guide</p></div><div class="body-grid"><article>'+sections+faq+'<div class="cta"><h2>Bring us the operation.</h2><p>Tell us what needs to happen, what you already use and where the work gets stuck. We will use the conversation to see whether there is a useful first step.</p><a class="button gold" href="'+esc(cta,quote=True)+'">Talk about this work</a></div></article><aside><h2>Related guides</h2>'+related+'</aside></div>'
    write(route.strip('/')+'/index.html',shell(g['title'],g['description'],route,body,True))
    for n,q in enumerate(g['queries'],1):queries.append({'query_id':f'GR-Q2-{i+1:02}-{n:02}','query':q,'audience':g['audience'],'target_url':HOST+route,'status':'HYPOTHESIS_NOT_VOLUME_VALIDATED'})

for i,a in enumerate(articles,1):
    route='/articles/'+a['slug']+'/'
    related=[g for g in guides if g['slug'] in a['related_guides']]
    bridge='<section><h2>Put the idea to work</h2><p>'+esc(a['reading_bridge'])+'</p><ul>'+''.join('<li><a href="/guides/'+g['slug']+'/">'+esc(g['title'])+'</a></li>' for g in related)+'</ul></section>'
    further=''.join('<a href="/articles/'+x['slug']+'/">'+esc(x['title'])+'</a>' for x in articles if x!=a)
    body='<div class="intro"><span class="eyebrow">'+esc(a['audience'])+'</span><h1>'+esc(a['title'])+'</h1><p class="answer">'+esc(a['answer'])+'</p><p class="byline">Published by Good Remedy · Article</p></div><div class="body-grid"><article>'+sections_html(a)+bridge+'</article><aside><h2>More articles</h2>'+further+'<a href="/guides/">Practical guides</a></aside></div>'
    write(route.strip('/')+'/index.html',shell(a['title'],a['description'],route,body,True))
    for n,q in enumerate(a['queries'],1):queries.append({'query_id':f'{series["query_prefix"]}-{i:02}-{n:02}','query':q,'audience':a['audience'],'target_url':HOST+route,'status':'HYPOTHESIS_NOT_VOLUME_VALIDATED'})

home=(ROOT/'baseline/index.html').read_text()
# Preserve all existing homepage content, forms, assets and metadata.
assert home.count('<footer')==1
module='<section id="practical-guides" class="paper" aria-label="Practical guides"><div class="shell"><div class="section-head"><p class="section-kicker">Explore the work</p><h2>AI implementation, from the request to the working operation.</h2><p>Practical guides for companies and implementation partners connecting people, AI and existing systems.</p></div><ul>'+''.join('<li><a href="/guides/'+g['slug']+'/">'+esc(g['title'])+'</a></li>' for g in guides)+'</ul><p><a class="button dark" href="/guides/">Browse practical guides</a></p></div></section>'
module=module.replace('</div></section>','<h3>Ideas about AI and work</h3><ul>'+''.join('<li><a href="/articles/'+a['slug']+'/">'+esc(a['title'])+'</a></li>' for a in articles)+'</ul><p><a href="/articles/">Read the articles</a></p></div></section>')
home=home.replace('<footer',module+'<footer',1)
home=home.replace('<div class="contact">','<div class="contact">'+RESOURCE_LINKS,1)
write('index.html',home)
paths=['/','/guides/','/articles/']+['/guides/'+g['slug']+'/' for g in guides]+['/articles/'+a['slug']+'/' for a in articles]
write('robots.txt','User-agent: *\nAllow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n\nSitemap: https://grmove.com/sitemap.xml\n')
write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+HOST+p+'</loc></url>' for p in paths)+'</urlset>\n')
write('.nojekyll','')
(ROOT/'operations/query-set.json').write_text(json.dumps(queries,indent=2)+'\n')
payload={'host':'grmove.com','key':key,'keyLocation':HOST+'/'+key+'.txt','urlList':[HOST+p for p in paths]}
(ROOT/'operations/indexnow-payload.json').write_text(json.dumps(payload,indent=2)+'\n')
manifest={'state':'BUILT_NOT_PUBLISHED','origin':HOST,'baseline_home_sha256':hashlib.sha256((ROOT/'baseline/index.html').read_bytes()).hexdigest(),
          'files':[{'path':str(p.relative_to(OUT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file()]}
(ROOT/'operations/build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'pages':len(paths),'buyer_queries':len(queries),'state':manifest['state']}))
