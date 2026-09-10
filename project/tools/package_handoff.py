"""Package the local publication candidate. Does not publish or submit URLs."""
import argparse, hashlib, html, json, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from html.parser import HTMLParser

R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();O=args.output.resolve();O.mkdir(parents=True,exist_ok=True)
D=R/'dist'
guides=json.loads((R/'content/guides.json').read_text())
articles=json.loads((R/'content/articles.json').read_text())
pieces=[('guides',g) for g in guides]+[('articles',a) for a in articles]
manifest=json.loads((R/'operations/build-manifest.json').read_text())

def command(tool,*args):
 result=subprocess.run([sys.executable,str(R/'tools'/tool),*args],capture_output=True,text=True,check=True)
 return json.loads(result.stdout)

validation=command('check.py')
(R/'operations/validation.json').write_text(json.dumps(validation,indent=2)+'\n')
measurement=command('measure.py','summary')
(R/'operations/measurement-status.json').write_text(json.dumps(measurement,indent=2)+'\n')
release={'state':'DRAFT_REVIEW_READY','authority_reference':'','build_manifest_sha256':hashlib.sha256((R/'operations/build-manifest.json').read_bytes()).hexdigest()}
(R/'operations/release-record.template.json').write_text(json.dumps(release,indent=2)+'\n')
disposition=json.loads((R/'operations/review-disposition.json').read_text())
disposition['editorial_extension']={'source':'Current user direction: pair original writing with buyer needs, felt problems and broader AI reading interests.','implemented':'Six revised guides, six series articles, reader-intent map and 48 proposed test queries.','publication':'NOT_PUBLISHED','search_volume':'NOT_MEASURED'}
(R/'operations/review-disposition.json').write_text(json.dumps(disposition,indent=2)+'\n')

# Combined offline reading preview. All public routes retain independent pages.
preview=(D/'guides/index.html').read_text()
preview=preview.replace('<h2>Ideas about AI and work</h2>','<h2 id="articles">Ideas about AI and work</h2>')
parts=[]
for kind,p in pieces:
 source=(D/kind/p['slug']/'index.html').read_text()
 main=re.search(r'<main[^>]*>(.*?)</main>',source,re.S).group(1)
 main=main.replace('<h1>','<h2>').replace('</h1>','</h2>')
 parts.append('<section id="'+p['slug']+'" class="full-guide">'+main+'</section>')
preview=preview.replace('</main>',''.join(parts)+'</main>')
preview=re.sub(r'href="/(?:guides|articles)/([^/]+)/"',r'href="#\1"',preview)
preview=preview.replace('href="/guides/"','href="#main"').replace('href="/articles/"','href="#articles"')
preview=preview.replace('href="/#','href="https://grmove.com/#').replace('href="/"','href="https://grmove.com/"')
preview=preview.replace('</style>','.full-guide{padding-top:36px;border-top:3px solid var(--gold);scroll-margin-top:100px}.full-guide .intro h2{font-size:clamp(2.3rem,5vw,4.5rem);line-height:1.05}</style>')
preview=preview.replace('<head>','<head><meta name="robots" content="noindex">')
preview=re.sub(r'<link rel="canonical"[^>]+>','',preview)
preview=re.sub(r'<script type="application/ld\+json">.*?</script>','',preview,flags=re.S)
preview=preview.replace('<title>AI implementation and operations: practical guides | Good Remedy</title>','<title>Good Remedy: guides and articles preview</title>')
(O/'Good_Remedy_Guides.html').write_text(preview)

# Extract visible copy from the exact generated HTML, with metadata and links.
class Copy(HTMLParser):
 def __init__(self,s):
  super().__init__();self.in_body=False;self.skip=0;self.words=[];self.links=[];self.feed(s)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='body':self.in_body=True
  if tag in ('script','style'):self.skip+=1
  if self.in_body and not self.skip:
   if tag in ('p','h1','h2','h3','li','section','summary','div','footer','nav'):self.words.append('\n\n')
   if tag=='a' and a.get('href'):self.links.append(a['href'])
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.skip-=1
  if tag=='body':self.in_body=False
  if tag in ('p','h1','h2','h3','li','section','summary','div','footer','nav'):self.words.append('\n\n')
 def handle_data(self,text):
  if self.in_body and not self.skip:self.words.append(text)
 def text(self):return re.sub(r'\n\s*\n(?:\s*\n)*','\n\n',''.join(self.words)).strip()

review=['# Good Remedy: exact publication candidate','','**Status: built for review; not published.**','','Six guides and six articles in a connected series now pair original GR ideas with direct needs, recognizable problems and adjacent AI interests. The public output has 15 HTML pages: the existing homepage with resource links, two indexes and twelve pieces. The one-file preview is for reading only.','','The article drafts adapt selected user archive ideas into new prose. They are not presented as verbatim historical articles, founder-signed copy, customer cases or independent reviews. The current September company brief governs scope. See reader-intent-map.md and series-editorial-provenance.json for the internal evidence trail. Exact founder extracts are held separately and excluded from this package.','','Public qualitative questions inform the editorial map; exact search volume, headline performance, indexing, AI citations and commercial results are unproved. No live result observations have been added.','','## Validation','','```json',json.dumps(validation,indent=2),'```','','Every page below is generated from the same HTML included in dist. Visible body wording is extracted in document order; typography and visual layout are shown in the preview. Destinations are listed separately.','','## Exact public pages']
for f in sorted(D.rglob('*.html')):
 s=f.read_text();ex=Copy(s)
 title=html.unescape(re.search(r'<title>(.*?)</title>',s,re.S).group(1))
 desc=re.search(r'<meta name="description" content="([^"]*)"',s)
 canonical=re.search(r'<link rel="canonical" href="([^"]*)"',s)
 review+=['','### '+str(f.relative_to(D)),'','Title: '+title,'','Description: '+(html.unescape(desc.group(1)) if desc else '(unchanged homepage metadata)'),'', 'Canonical: '+(canonical.group(1) if canonical else '(none)'),'',ex.text(),'','Link destinations:']
 review+=['- '+x for x in dict.fromkeys(ex.links)]
review+=['','## Exact discovery files']
for name in ['sitemap.xml','robots.txt']:review+=['','### '+name,'','```text',(D/name).read_text().strip(),'```']
review+=['','## Exact measurement schema','','The 24 guide questions retain their text and GR-Q2 IDs. Twenty-four series questions use GR-A2 IDs. The expanded set has a different digest; its rows remain hypotheses, not observed searches. The prior 24-query set is retained as operations/query-set.guides-v2.json.','','```json',(R/'operations/measurement-schema.json').read_text().strip(),'```','','## Publication and evidence limits','','Each proposed integration requires its own access and feasibility check. The copy claims no universal connector coverage, universal reliability, quantified cost advantage or demonstrated client outcomes.','','The release template is DRAFT_REVIEW_READY with a blank authority reference. Record actual copy approval through the existing process before publication. IndexNow also checks the approved manifest and deployed bytes. It cannot establish indexing or ranking. The discovery setup allows normal search access; there is no direct placement in AI answers.','','Official guidance used in the existing discovery design: [Google spam policies](https://developers.google.com/search/docs/essentials/spam-policies), [OpenAI publisher guidance](https://help.openai.com/en/articles/12627856), [IndexNow documentation](https://www.indexnow.org/documentation).']
review_text='\n'.join(review)+'\n'
(R/'review/publication-review.md').write_text(review_text)
(O/'GR_Publication_Review_2026-09-09.md').write_text(review_text)

readout='''# What we made for grmove.com

September 9, 2026. Updated publication candidate for Jeff.

**A branded reading section connecting what prospective buyers care about with Good Remedy’s original thinking.**

Readers have three ways in: a direct implementation question, a problem they recognize from their working day, or a broader AI article that interests them. The guides explain useful work and possible delivery. The six-part series examines drift, hallucination, deception, hidden agendas and consciousness, then explains how models can help define work and build a useful operating system. Each piece explains the behavior, causes, practical checks and a productive next movement. The intended horizon is the connected business operation.

## What changed

- Strengthened six practical guides using selected user passages from the writing archive and the current company brief.
- Added a six-part AI series, each on its own crawlable route, plus an Articles index.
- Revised article titles to lead with a familiar spoken reaction and name the AI issue. Descriptions and related-reading copy pair that issue with relevant implementation needs, including workflow automation, system integration, agent verification and workplace adoption.
- Paired each piece with its intended reader, reason to click, distinctive GR contribution, source evidence and an appropriate next step.
- Kept the existing logo, colors, typography, navigation and footer. Added visible Articles links alongside Practical guides, with links between relevant pieces.
- Expanded the proposed measurement set to 48 questions: 24 existing guide questions and 24 article questions. Mention, citation, placement and actual inquiry remain separate outcomes.

## The guides

'''+ '\n'.join('- '+g['title'] for g in guides)+'''

## The articles

'''+ '\n'.join('- '+a['title'] for a in articles)+'''

## Source and demand boundary

Seven archive JSON files were inspected selectively; this was not a full-corpus read. The new prose adapts the founder’s ideas and examples, with the current September company brief governing what GR offers. It is not a claim that these are verbatim previously authored articles. Raw archives, exact source extracts and private source documents are excluded from the package. Public scientific claims link to primary research. Consciousness remains an open question; controlled deception experiments are not reported as ordinary-use prevalence. The public prose excludes proprietary grammar, internal prompts and implementation mechanisms.

Public questions support qualitative language about connecting teams and choosing implementation help. Primary research substantiates the series topics and bounded findings. They do not establish keyword volume, headline click-through or qualified demand. Some guide topics remain editorial hypotheses. See 05_Reader_Intent_Map.md for the mapping and source links.

## Delivery and verified state

There are 15 HTML pages and 19 public files under project/dist/: the existing homepage with additions, two indexes, six guides, six articles and four discovery/static-hosting files. The full handoff also contains editable copy, build tools, measurement tools, exact publication copy and this readout.

Local checks passed for routes, internal links, metadata, embedded logos, preservation of the baseline homepage, crawl directives, file integrity, release safeguards and measurement evidence handling. The preview contains all twelve pieces in one HTML file.

Nothing has been published or submitted for indexing. Browser and live-site checks remain. No search baseline, AI recommendation result, traffic or lead has been demonstrated. The packet does not install analytics, schedule collection, query model accounts automatically or send messages.

Jeff’s next step is to review the candidate copy, then use the existing website release process with 02_Jeff_Publishing_Instructions.md. Only the contents of project/dist/ belong on the public site. If the homepage changed after the saved baseline, merge its resource additions into the current homepage.
'''
(O/'GR_Jeff_Readout_2026-09-09.md').write_text(readout)
(O/'GR_Search_Discovery_Readout_2026-09-09.md').write_text(readout)

# Preserve the established installation instructions, updating the content scope.
instruction_path=O/'GR_Jeff_Publishing_Instructions_2026-09-09.md'
instructions=instruction_path.read_text()
instructions=instructions.replace('The preview places all six guides in one file for reading. The public site uses six separate pages plus an index.','The preview places six guides and six articles in one file for reading. The public site uses twelve separate content pages plus Guides and Articles indexes.')
instructions=instructions.replace('The added footer link is labeled Practical guides and points to /guides/.','The added footer links are Practical guides at /guides/ and Articles at /articles/. The resource section also includes the article titles.')
instructions=instructions.replace('| sitemap.xml | Lists homepage, index and six guides |','| articles/index.html | Articles landing page at /articles/ |\n'+ '\n'.join('| articles/'+a['slug']+'/index.html | '+a['title']+' |' for a in articles)+'\n| sitemap.xml | Lists all 15 public HTML routes |')
instructions=instructions.replace('change content/guides.json and run','change content/guides.json or content/articles.json and run')
instructions=instructions.replace('Use project/operations/query-set.json: 24 exact questions with GR-Q2 identifiers. The older query set is retained for history and should not be mixed into this comparison.','Use project/operations/query-set.json: 48 proposed questions. The 24 guide questions keep GR-Q2 identifiers and unchanged question text; 24 series questions use GR-A2 identifiers. The prior 24-query set is retained in query-set.guides-v2.json. The expanded set has a different digest and should be reported as a separate set. These are test phrases, not measured search-volume data.')
instructions=instructions.replace('- Each guide opens directly, with its own heading and complete answer.','- Each guide and article opens directly, with its own heading and complete text.')
instructions=instructions.replace('- Homepage guide links, the index, related guides and the footer route work.','- Homepage resource links, both indexes, related articles/guides and both footer routes work.')
instructions=instructions.replace('The actual guide pages have their own canonical URLs','The actual guide and article pages have their own canonical URLs')
instructions=instructions.split('\n## Reader-interest review\n')[0].rstrip()+'\n\n## Reader-interest review\n\n05_Reader_Intent_Map.md pairs every piece with an intended reader, a reason to arrive and the GR idea that rewards reading. Articles can build understanding before the person is looking for a provider. Publication does not certify search demand. Use actual query, click and inquiry evidence to develop the next topics. No new analytics or tracking has been installed.\n'
instructions=re.sub(r'(?m)^\| articles/.*\n','',instructions)
article_rows='| articles/index.html | The six-part AI series index |\n'+'\n'.join('| articles/'+a['slug']+'/index.html | '+a['title']+' |' for a in articles)+'\n'
instructions=instructions.replace('| sitemap.xml |',article_rows+'| sitemap.xml |',1)
instructions=instructions.replace('Lists all 12 public HTML routes','Lists all 15 public HTML routes').replace('six guides and three articles','six guides and six articles').replace('nine separate content pages','twelve separate content pages')
instructions=re.sub(r'Use project/operations/query-set.json:.*?(?=\n\n)','Use project/operations/query-set.json: 48 proposed questions. The 24 guide questions retain GR-Q2 identifiers and unchanged text. Twenty-four series questions use GR-A2 identifiers. The earlier 36-query set is retained as query-set.articles-v1.json; its GR-A1 article questions are historical. The new set has a different digest. Search volume and headline performance remain unmeasured.',instructions,flags=re.S)
instruction_path.write_text(instructions)
(R/'README.md').write_text('''# Good Remedy reading and search-discovery candidate

Static addition to the existing externally hosted grmove.com website. No deployment is performed by these tools.

Six guides and six articles live in content/guides.json and content/articles.json. Run python tools/build.py and python tools/check.py after changing public copy. The 15 built HTML pages and four support files are in dist/. Publish only dist contents through the existing website process, after copy review and reconciliation with newer homepage work.

Use the existing handoff publishing instructions for release, IndexNow and measurement. The 48 proposed test questions in operations/query-set.json include the unchanged 24 GR-Q2 guide questions and 24 GR-A2 series questions. The previous 36-query set is preserved in query-set.articles-v1.json. Query-set hashes prevent treating changed experiments as unchanged results. No baseline captures exist.

The preview is a noindex reading artifact, excluded from dist. Generate the handoff with python tools/package_handoff.py --output /absolute/path/to/existing-handoff-output-directory. The packaging command expects the existing publishing-instructions Markdown in that directory, preserves its installation guidance and updates scope. It does not publish or upload.

Review reader-intent-map.md for the qualitative evidence and archive-editorial-provenance.json for selected source pointers. These are internal editorial records. Articles are newly adapted drafts, not verbatim archived writing. No raw archive, private source documents, measured keyword volume, invented attribution or fabricated customer proof is included.
''')

H=O/'GR_Jeff_Website_Handoff_2026-09-09'
with tempfile.TemporaryDirectory(dir=O,prefix='gr-handoff-') as temporary:
 stage=Path(temporary)/H.name;stage.mkdir()
 shutil.copytree(R,stage/'project',ignore=shutil.ignore_patterns('__pycache__'))
 (stage/'preview').mkdir()
 shutil.copy2(O/'Good_Remedy_Guides.html',stage/'preview/Good_Remedy_Guides.html')
 for source,dest in [(O/'GR_Jeff_Readout_2026-09-09.md','01_What_We_Made.md'),(instruction_path,'02_Jeff_Publishing_Instructions.md'),(O/'GR_Publication_Review_2026-09-09.md','03_Publication_Review.md'),(R/'review/reader-intent-map.md','05_Reader_Intent_Map.md')]:shutil.copy2(source,stage/dest)
 urls=['https://grmove.com/'+p['path'].removesuffix('index.html') for p in manifest['files'] if p['path'].endswith('index.html')]
 (stage/'04_Live_URL_Checklist.md').write_text('# Live URL checklist\n\nTarget routes, not verified live pages.\n\n'+'\n'.join('- [ ] '+u for u in urls)+'\n\n- [ ] Phone and desktop presentation\n- [ ] Existing homepage form and assets\n- [ ] Both indexes, related reading and footer links\n- [ ] Mailto opens the correct draft without sending\n- [ ] Sitemap, robots and IndexNow key file reachable\n- [ ] Actual copy approval and deployed version recorded\n- [ ] Real indexing receipt, if submitted\n')
 logo=re.search(r'<nav\b.*?<img src="([^"]+)"',(R/'baseline/index.html').read_text(),re.S).group(1)
 start='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Good Remedy: website handoff</title><style>body{margin:0;background:#f4f1e8;color:#111820;font:18px/1.65 system-ui,sans-serif}main{max-width:920px;margin:auto;padding:36px 24px 80px}header{padding:24px;background:#071521;color:white}header img{width:50px;vertical-align:middle;margin-right:15px}h1{font-size:clamp(2.3rem,6vw,4rem);line-height:1.05}a{color:#224f73}nav{display:flex;flex-wrap:wrap;gap:16px}nav a{background:#efc94b;color:#071521;border-radius:30px;padding:12px 20px;text-decoration:none;font-weight:700}.notice{background:white;padding:22px;border-left:5px solid #d4a928;margin:30px 0}a:focus-visible{outline:3px solid #d4a928;outline-offset:4px}</style></head><body><header><img src="'''+logo+'''" alt="Good Remedy logo">Good Remedy / Jeff’s website handoff</header><main><h1>Good ideas. Useful guides. One GR website.</h1><p>Six buyer guides and six articles in the AI series, grounded in GR’s writing and paired with reasons the intended reader would arrive.</p><nav><a href="preview/Good_Remedy_Guides.html">Read the preview</a><a href="01_What_We_Made.md">What we made</a><a href="05_Reader_Intent_Map.md">Reader and buyer pairing</a></nav><div class="notice"><strong>Only project/dist/ contents go on the public website.</strong><p>The preview, source files and internal review records stay outside the public output. Review the copy and merge any newer homepage changes before publication.</p></div><ol><li>Read <a href="03_Publication_Review.md">the exact publication copy</a>.</li><li>Follow <a href="02_Jeff_Publishing_Instructions.md">the publishing instructions</a>.</li><li>Check <a href="04_Live_URL_Checklist.md">the live routes</a> after deployment.</li><li>Record actual discovery and inquiry results using the included measurement tools.</li></ol><p>Current state: local checks passed; not published. Search volume, headline response, indexing, citations and leads are unproved.</p></main></body></html>'''
 (stage/'00_START_HERE.html').write_text(start)
 for link in re.findall(r'href="([^"]+)"',start):assert (stage/link).is_file()
 inventory=[{'path':str(p.relative_to(stage)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'publishable':p.is_relative_to(stage/'project/dist')} for p in sorted(stage.rglob('*')) if p.is_file()]
 assert sum(x['publishable'] for x in inventory)==len(manifest['files'])
 (stage/'PACKAGE_MANIFEST.json').write_text(json.dumps({'status':'BUILT_NOT_PUBLISHED','public_files':len(manifest['files']),'files':inventory},indent=2)+'\n')
 z=O/'GR_Jeff_Complete_Website_Handoff_2026-09-09.zip'
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as archive:
  for p in sorted(stage.rglob('*')):
   if p.is_file():archive.write(p,str(p.relative_to(Path(temporary))))
 with zipfile.ZipFile(z) as archive:
  assert archive.testzip() is None
  for p in manifest['files']:assert hashlib.sha256(archive.read(H.name+'/project/dist/'+p['path'])).hexdigest()==p['sha256']
 if H.exists():shutil.rmtree(H)
 shutil.copytree(stage,H)

candidate=O/'GR_Search_Discovery_Candidate_2026-09-09.zip'
with zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as archive:
 for p in sorted(R.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:archive.write(p,'gr-search-discovery/'+str(p.relative_to(R)))
ids=set(re.findall(r'\bid="([^"]+)"',preview))
for target in re.findall(r'href="#([^"]+)"',preview):assert target in ids,target
print(json.dumps({'validation':validation,'handoff_archive_verified':True,'public_files':len(manifest['files']),'guides':6,'articles':len(articles),'preview_anchors':'PASS','publication':'NOT_PUBLISHED'}))
