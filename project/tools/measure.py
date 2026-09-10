"""Record actual results, preserve evidence and separate discovery from context effects."""
import argparse,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['schema_version','run_id','run_number','query_id','exact_prompt','platform','model_label','observed_at','fresh_session','prior_gr_context','search_enabled','session_context','capture_complete','answer_text','cited_urls','gr_mentioned','gr_recommended','gr_answer_position','position_basis','position_excerpt','gr_click_worthy','positioning_rationale','entities_alongside','observer','screenshot_file']
def fail(message):raise SystemExit(message)
def valid_url(u):
 try:return isinstance(u,str) and urlsplit(u).scheme in ['http','https'] and bool(urlsplit(u).hostname)
 except ValueError:return False
def gr_url(u):return urlsplit(u).hostname in ['grmove.com','www.grmove.com']
def validate(x,queries):
 if not isinstance(x,dict):fail('Capture must be an object')
 if set(x)!=set(FIELDS):fail('Capture fields differ from v2 schema: '+', '.join(sorted(set(FIELDS)^set(x))))
 if x['schema_version']!=2:fail('Use capture schema version 2')
 if type(x['run_number']) is not int or x['run_number']<1:fail('Run number must be a positive integer')
 if not isinstance(x['query_id'],str) or x['query_id'] not in queries or x['exact_prompt']!=queries[x['query_id']]['query']:fail('Prompt differs from the fixed query set; create a separate experiment')
 for k in ['run_id','platform','model_label','session_context','answer_text','observer','positioning_rationale']:
  if not isinstance(x[k],str) or not x[k].strip():fail('Empty or invalid '+k)
 for k in ['fresh_session','capture_complete','gr_mentioned','gr_recommended']:
  if type(x[k]) is not bool:fail('Boolean required for '+k)
 for k in ['prior_gr_context','search_enabled','gr_click_worthy']:
  if x[k] is not None and type(x[k]) is not bool:fail('Boolean or null required for '+k)
 if not x['capture_complete']:fail('Save the complete result before recording this observation')
 if not isinstance(x['cited_urls'],list) or not all(valid_url(u) for u in x['cited_urls']):fail('Invalid cited URLs')
 if len(set(x['cited_urls']))!=len(x['cited_urls']):fail('Duplicate cited URL')
 if x['gr_recommended'] and not x['gr_mentioned']:fail('Recommendation requires mention')
 if x['gr_click_worthy'] and not any(gr_url(u) for u in x['cited_urls']):fail('Click-worthy placement requires an actual GR link in the captured result')
 pos=x['gr_answer_position'];basis=x['position_basis']
 if basis not in ['numbered_list','paragraph','unranked','not_present']:fail('Unknown position basis')
 if basis in ['numbered_list','paragraph']:
  if type(pos) is not int or pos<1 or not x['gr_mentioned']:fail('A position needs a positive ordinal and a mention')
 elif pos is not None:fail('Unranked/absent results have no numeric position')
 if (basis=='not_present') != (not x['gr_mentioned']):fail('Position basis conflicts with mention')
 if not isinstance(x['position_excerpt'],str) or (x['gr_mentioned'] and not x['position_excerpt'].strip()) or (x['position_excerpt'] and x['position_excerpt'] not in x['answer_text']):fail('Position excerpt must appear verbatim in the captured answer')
 if not isinstance(x['entities_alongside'],list):fail('Entities alongside must be a list')
 for e in x['entities_alongside']:
  if not isinstance(e,dict) or set(e)!={'name','relationship','cited_urls'} or not isinstance(e['name'],str) or not e['name'].strip() or e['relationship'] not in ['competitor','other'] or not isinstance(e['cited_urls'],list) or any(u not in x['cited_urls'] for u in e['cited_urls']):fail('Invalid alongside entity or citation not present in result')
 try:
  if datetime.fromisoformat(x['observed_at'].replace('Z','+00:00')).tzinfo is None:fail('Observation timestamp needs timezone')
 except (ValueError,AttributeError):fail('Invalid observation timestamp')
 if x['screenshot_file'] is not None:
  if not isinstance(x['screenshot_file'],str) or not Path(x['screenshot_file']).is_file() or Path(x['screenshot_file']).suffix.lower() not in ['.png','.jpg','.jpeg','.webp']:fail('Screenshot must be an existing image file or null')
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
 r=sub.add_parser('record');r.add_argument('--capture',type=Path,required=True)
 sub.add_parser('summary');a=p.parse_args()
 query_bytes=(ROOT/'operations/query-set.json').read_bytes();query_hash=hashlib.sha256(query_bytes).hexdigest()
 queries={q['query_id']:q for q in json.loads(query_bytes)}
 dest=ROOT/'operations/captures';dest.mkdir(exist_ok=True)
 if a.action=='record':
  x=json.loads(a.capture.read_text());validate(x,queries)
  identity=hashlib.sha256(json.dumps([x['run_id'],x['run_number'],x['query_id'],x['platform']]).encode()).hexdigest();f=dest/(identity+'.json')
  if f.exists():fail('Observation already recorded for this run/number/query/platform')
  shot=x.pop('screenshot_file')
  if shot:
   raw=Path(shot).read_bytes();digest=hashlib.sha256(raw).hexdigest();folder=ROOT/'operations/evidence';folder.mkdir(exist_ok=True)
   target=folder/(digest+Path(shot).suffix.lower());target.write_bytes(raw)
   x['screenshot_evidence']={'path':str(target.relative_to(ROOT)),'sha256':digest}
  else:x['screenshot_evidence']=None
  x['gr_cited_urls']=[u for u in x['cited_urls'] if gr_url(u)]
  x['context_eligible']=x['fresh_session'] and x['prior_gr_context'] is False and x['search_enabled'] is True
  x['query_set_sha256']=query_hash
  x['answer_sha256']=hashlib.sha256(x['answer_text'].encode()).hexdigest()
  x['recorded_at']=datetime.now(timezone.utc).isoformat()
  x['capture_sha256']=hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  with f.open('x') as file:file.write(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
  print('Recorded '+x['query_id']);return
 rows=[json.loads(f.read_text()) for f in dest.glob('*.json')];groups={};legacy=0
 for x in rows:
  if x.get('schema_version')!=2:legacy+=1;continue
  cohort='fresh_search' if x['context_eligible'] else 'context_affected_or_unknown'
  dimensions=[x['run_id'],x['run_number'],x['platform'],x['model_label'],x['query_set_sha256'],cohort]
  key=json.dumps(dimensions)
  g=groups.setdefault(key,dict(run_id=x['run_id'],run_number=x['run_number'],platform=x['platform'],model_label=x['model_label'],query_set_sha256=x['query_set_sha256'],cohort=cohort,observations=0,queries_observed=set(),mentions=0,recommendations=0,gr_citations=0,click_worthy_judgments=0,click_worthy_unknown=0,positions=[]))
  g['observations']+=1;g['queries_observed'].add(x['query_id']);g['mentions']+=x['gr_mentioned'];g['recommendations']+=x['gr_recommended'];g['gr_citations']+=bool(x['gr_cited_urls'])
  g['click_worthy_judgments']+=x['gr_click_worthy'] is True;g['click_worthy_unknown']+=x['gr_click_worthy'] is None
  if x['gr_answer_position'] is not None:g['positions'].append({'query_id':x['query_id'],'basis':x['position_basis'],'ordinal':x['gr_answer_position']})
 for g in groups.values():
  g['queries_observed']=len(g['queries_observed']);g['queries_not_observed']=len(queries)-g['queries_observed'] if g['query_set_sha256']==query_hash else None
  g['mention_rate_observed']=g['mentions']/g['observations'];g['citation_rate_observed']=g['gr_citations']/g['observations'];g['recommendation_rate_observed']=g['recommendations']/g['observations']
 print(json.dumps({'status':'OBSERVED_CAPTURES' if rows else 'NOT_RUN','fixed_queries':len(queries),'groups':list(groups.values()),'legacy_records_excluded':legacy,'limits':'Actual captures with human judgments. Fresh-search cohort requires fresh session, no known prior GR context and search enabled. This is not causal attribution. Click-worthy is a recorded judgment, not click-through rate; list and paragraph positions are not comparable ranks.'},indent=2))
if __name__=='__main__':main()
