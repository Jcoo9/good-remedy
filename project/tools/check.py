"""Check generated routes, metadata, preservation and operational safeguards."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,subprocess,sys,tempfile,shutil
from urllib.parse import urlsplit
R=Path(__file__).resolve().parents[1];D=R/'dist'
class Page(HTMLParser):
 def __init__(self,s):
  super().__init__();self.links=[];self.ids=[];self.h1=0;self.canonical=[];self.feed(s)
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='h1':self.h1+=1
  if 'id' in a:self.ids.append(a['id'])
  if t=='a' and 'href'in a:self.links.append(a['href'])
  if t=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
pages={('/' if p==D/'index.html' else '/'+str(p.parent.relative_to(D))+'/'):Page(p.read_text()) for p in D.rglob('*.html')}
expected_pages=3+len(json.loads((R/'content/guides.json').read_text()))+len(json.loads((R/'content/articles.json').read_text()))
assert len(pages)==expected_pages
for route,p in pages.items():
 assert p.h1==1,(route,'h1')
 assert p.canonical==['https://grmove.com'+route],(route,'canonical')
 for link in p.links:
  u=urlsplit(link)
  if u.scheme or u.netloc:continue
  target=u.path or route
  if not target.startswith('/'):continue
  assert target in pages,(route,link)
  if u.fragment:assert u.fragment in pages[target].ids,(route,link)
 for script in re.findall(r'<script type="application/ld\+json">(.*?)</script>',(D/route.strip('/')/'index.html').read_text(),re.S):json.loads(script)
home=(D/'index.html').read_text();base=(R/'baseline/index.html').read_text()
restored=re.sub(r'<section id="practical-guides".*?</section>','',home,flags=re.S)
restored=restored.replace('<div><a href="/guides/">Practical guides</a></div>','',1)
restored=restored.replace('<div><a href="/articles/">Articles</a></div>','',1)
assert restored==base
from urllib.robotparser import RobotFileParser
robots=RobotFileParser();robots.parse((D/'robots.txt').read_text().splitlines())
for agent in ['OAI-SearchBot','Googlebot','bingbot']:
 for route in pages:assert robots.can_fetch(agent,'https://grmove.com'+route)
logo=re.search(r'<nav\b.*?<img src="([^"]+)"',base,re.S).group(1)
for path in [* (D/'guides').rglob('*.html'),* (D/'articles').rglob('*.html')]:
 text=path.read_text();assert text.count(logo)==2;assert 'href="/guides/">Practical guides' in text;assert 'noindex' not in text
assert len({p.canonical[0] for p in pages.values()})==expected_pages
assert 'Sitemap: https://grmove.com/sitemap.xml' in (D/'robots.txt').read_text()
assert (D/'sitemap.xml').read_text().count('<loc>')==expected_pages
manifest=json.loads((R/'operations/build-manifest.json').read_text())
for f in manifest['files']:assert hashlib.sha256((D/f['path']).read_bytes()).hexdigest()==f['sha256']
def run(root,*args):return subprocess.run([sys.executable,str(root/'tools'/args[0]),*args[1:]],capture_output=True,text=True)
assert json.loads(run(R,'indexnow.py').stdout)['mode']=='DRY_RUN'
assert run(R,'indexnow.py','--submit').returncode!=0
assert run(R,'indexnow.py','--submit','--release-record',str(R/'operations/release-record.template.json')).returncode!=0
observation_status=json.loads(run(R,'measure.py','summary').stdout)['status']
# Isolated synthetic fixtures exercise logic; they never enter observation evidence.
with tempfile.TemporaryDirectory() as t:
 x=Path(t)/'candidate';shutil.copytree(R,x,ignore=shutil.ignore_patterns('captures','evidence'))
 c=json.loads((x/'operations/capture.template.json').read_text())
 assert run(x,'measure.py','record','--capture',str(x/'operations/capture.template.json')).returncode!=0
 c.update(platform='TEST',model_label='fixture',observed_at='2026-09-09T00:00:00Z',fresh_session=True,prior_gr_context=False,search_enabled=True,capture_complete=True,session_context='ISOLATED TEST ONLY',answer_text='Synthetic fixture: Good Remedy. https://grmove.com/',observer='test',gr_mentioned=True,gr_recommended=True,position_basis='numbered_list',gr_answer_position=1,position_excerpt='Good Remedy',cited_urls=['https://grmove.com/'],gr_click_worthy=True,positioning_rationale='SYNTHETIC TEST ONLY')
 f=x/'fixture.json';f.write_text(json.dumps(c))
 assert run(x,'measure.py','record','--capture',str(f)).returncode==0
 assert run(x,'measure.py','record','--capture',str(f)).returncode!=0
 bad={**c,'run_number':2,'cited_urls':[]};f.write_text(json.dumps(bad))
 assert run(x,'measure.py','record','--capture',str(f)).returncode!=0
 # A contextual mention without citation is preserved but cannot enter fresh-search cohort.
 c.update(run_number=2,prior_gr_context=True,cited_urls=[],gr_click_worthy=False)
 f.write_text(json.dumps(c));assert run(x,'measure.py','record','--capture',str(f)).returncode==0
 summary=json.loads(run(x,'measure.py','summary').stdout)
 fresh=next(g for g in summary['groups'] if g['cohort']=='fresh_search')
 affected=next(g for g in summary['groups'] if g['cohort']=='context_affected_or_unknown')
 assert fresh['observations']==1 and fresh['gr_citations']==1 and fresh['click_worthy_judgments']==1
 assert affected['mentions']==1 and affected['gr_citations']==0
 records=list((x/'operations/captures').glob('*.json'));assert len(records)==2
 for record in records:
  data=json.loads(record.read_text());digest=data.pop('capture_sha256')
  assert hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==digest
print(json.dumps({'result':'PASS','pages':len(pages),'queries':len(json.loads((R/'operations/query-set.json').read_text())),'homepage_original_content_preserved':True,'brand_logo_every_content_page':'PASS','internal_links_and_metadata':'PASS','robot_access':'PASS','manifest_hashes':'PASS','indexnow_release_gates':'PASS','measurement_capture_hashes_duplicates_and_context_separation':'PASS','actual_recommendation_evaluation':observation_status,'browser_visual_qa':'NOT_RUN'}))
