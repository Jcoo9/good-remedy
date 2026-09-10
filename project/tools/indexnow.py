"""Prepare by default; submit only approved, deployed bytes to IndexNow."""
import argparse,hashlib,json,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run():
 p=argparse.ArgumentParser();p.add_argument('--submit',action='store_true');p.add_argument('--release-record',type=Path);a=p.parse_args()
 payload=json.loads((ROOT/'operations/indexnow-payload.json').read_text())
 if not a.submit:print(json.dumps({'mode':'DRY_RUN','endpoint':'https://api.indexnow.org/indexnow','payload':payload},indent=2));return
 if not a.release_record:raise SystemExit('A recorded publication approval and live deployment are required')
 release=json.loads(a.release_record.read_text())
 manifest=(ROOT/'operations/build-manifest.json').read_bytes()
 if release.get('state')!='APPROVED_FOR_PUBLICATION' or not release.get('authority_reference') or release.get('build_manifest_sha256')!=hashlib.sha256(manifest).hexdigest():raise SystemExit('Release record does not authorize this exact build')
 m=json.loads(manifest)
 # Verify all added/deployed files, not merely an indexing request's acknowledgement.
 for f in m['files']:
  if f['path']=='.nojekyll':continue
  path=f['path'];url=payload['keyLocation'] if path==payload['key']+'.txt' else 'https://grmove.com/'+path
  if path=='index.html':url='https://grmove.com/'
  elif path.endswith('/index.html'):url='https://grmove.com/'+path[:-10]
  with urllib.request.urlopen(url,timeout=20) as r:
   if r.url!=url or r.status!=200 or hashlib.sha256(r.read()).hexdigest()!=f['sha256']:raise SystemExit('Live bytes do not match approved build: '+path)
 request=urllib.request.Request('https://api.indexnow.org/indexnow',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 receipt={'at':datetime.now(timezone.utc).isoformat(),'urls':payload['urlList'],'meaning':'Receipt is notification acknowledgement, not indexing, ranking or AI recommendation proof.'}
 try:
  with urllib.request.urlopen(request,timeout=30) as r:receipt.update(http_status=r.status,body=r.read().decode()[:2000])
 except urllib.error.HTTPError as e:receipt.update(http_status=e.code,body=e.read().decode()[:2000])
 receipt['state']='ACKNOWLEDGED' if receipt['http_status']==200 else 'KEY_VALIDATION_PENDING' if receipt['http_status']==202 else 'FAILED'
 dest=ROOT/'operations'/('indexnow-receipt-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
 dest.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':run()
