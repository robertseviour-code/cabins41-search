"""Cabins41 source checker. Collects leads; does NOT verify actual cruise offers."""
import argparse,datetime,json,pathlib,re,time,urllib.request,urllib.error,html
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).parent
SOURCES=json.loads((ROOT/'sources.json').read_text())
PATTERN=re.compile(r'(?i)solo\s+cruis|single\s+supplement|single\s+cabins?|alleinreisend|einzelkabine|suplemento\s+individual|cruceros?\s+para\s+(?:una|uno|solos?)')
def check(src):
 req=urllib.request.Request(src['url'],headers={'User-Agent':'Mozilla/5.0 (compatible; Cabins41Research/1.0)'})
 try:
  with urllib.request.urlopen(req,timeout=20) as response:
   raw=response.read(500000).decode('utf-8','replace')
   final=response.geturl()
  cleaned=html.unescape(re.sub(r'<[^>]*>',' ',re.sub(r'(?is)<(script|style).*?</\1>',' ',raw)))
  cleaned=re.sub(r'\s+',' ',cleaned)
  matches=list(PATTERN.finditer(cleaned))
  snippets=list(dict.fromkeys(cleaned[max(0,m.start()-90):m.end()+160].strip() for m in matches[:8]))
  return {'status':'checked','url':final,'lead_snippets':snippets,'lead_count':len(matches),'note':'Keyword leads only; individual dated solo cruise offers NOT verified.'}
 except Exception as e:return {'status':'failed','error':str(e)[:300],'lead_snippets':[],'lead_count':0}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--date');ap.add_argument('--no-wait',action='store_true');ap.add_argument('--one',type=int);a=ap.parse_args()
 date=a.date or datetime.datetime.now(ZoneInfo('Europe/London')).date().isoformat()
 out=ROOT/'data'/f'holding-{date}.json';out.parent.mkdir(exist_ok=True)
 ledger=json.loads(out.read_text()) if out.exists() else {'date':date,'results':{},'description':'Source-level keyword discovery; not verified cruise offers'}
 for src in SOURCES:
  key=str(src['id'])
  if a.one and src['id']!=a.one:continue
  if key in ledger['results'] and ledger['results'][key]['status']=='checked':continue
  result=check(src);result.update({'source_name':src['name'],'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  ledger['results'][key]=result
  out.write_text(json.dumps(ledger,ensure_ascii=False,indent=2))
  print(f"{src['id']}/85 {src['name']}: {result['status']}, keyword matches {result['lead_count']}",flush=True)
  if not a.no_wait and not a.one:time.sleep(20)
 completed=sum(v['status']=='checked' for v in ledger['results'].values())
 failed=sum(v['status']=='failed' for v in ledger['results'].values())
 print(f'Finished: {completed} checked, {failed} failed, {85-completed-failed} unattempted. No individual offers verified.')
if __name__=='__main__':main()
