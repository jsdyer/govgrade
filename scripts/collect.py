#!/usr/bin/env python3
"""Bounded provider collection. Only the owned CoolCode target is enabled by default."""
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from archive import fetch, manifest, save, timestamp, utcnow

ROOT=Path(__file__).resolve().parents[1]
OBS='https://observatory-api.mdn.mozilla.net/api/v2/analyze'
SSL='https://api.ssllabs.com/api/v4/'
GRADES={'A+','A','A-','B+','B','B-','C+','C','C-','D+','D','D-','E','F'}

def normalize_observatory(data):
    scan=data.get('scan')
    if not isinstance(scan,dict): raise ValueError('Missing Observatory scan')
    if scan.get('error'):
        return {'state':'provider_error','message':str(scan['error']),'grade':None,'tests':[],'history':[]}
    grade=scan.get('grade');score=scan.get('score');version=scan.get('algorithm_version')
    if grade not in GRADES or isinstance(score,bool) or not isinstance(score,(int,float)) or not -1000<=score<=200 or not isinstance(version,int):
        raise ValueError('Invalid Observatory grade, score or method')
    timestamp(scan['scanned_at'])
    tests=[]
    for key,value in data.get('tests',{}).items():
        if not isinstance(value,dict) or value.get('pass') not in [True,False,None]: raise ValueError('Invalid test result')
        tests.append({'id':str(key),'title':str(value.get('title',key)), 'pass':value.get('pass'),
                      'result':str(value.get('result','not supplied')), 'score_modifier':value.get('score_modifier')})
    if not tests: raise ValueError('Missing provider test evidence')
    history=[]
    for item in data.get('history',[]):
        if item.get('grade') not in GRADES or not isinstance(item.get('score'),(int,float)): continue
        timestamp(item['scanned_at'])
        history.append({'id':item.get('id'),'grade':item['grade'],'score':item['score'],'scanned_at':item['scanned_at'],
                        'algorithm_version':version if item.get('id')==scan.get('id') else None})
    return {'state':'ready','grade':grade,'score':score,'scanned_at':scan['scanned_at'],'algorithm_version':version,'scan_id':scan.get('id'),
            'tests_passed':scan.get('tests_passed'),'tests_failed':scan.get('tests_failed'),'tests_quantity':scan.get('tests_quantity'),
            'tests':tests,'history':sorted(history,key=lambda x:x['scanned_at'],reverse=True)[:20]}

def ssl_allowed(config,site,email):
    # fromCache is NOT cache-only. It may initiate an assessment on a cache miss.
    # Target-owner permission alone does not permit public-site API publication.
    return bool(email and config.get('ssl_labs_publication_permission') and site.get('owner_permission')
                and site.get('publication_permission') and site.get('ssl_labs_enabled'))

def normalize_ssl(data):
    status=data.get('status')
    if status not in {'READY','ERROR','DNS','IN_PROGRESS'}: raise ValueError('Unknown SSL Labs state')
    result={'state':status.lower(),'message':str(data.get('statusMessage','')),'grade':None,'endpoints':[],
            'test_time':data.get('testTime'),'engine_version':data.get('engineVersion'),'criteria_version':data.get('criteriaVersion')}
    for endpoint in data.get('endpoints',[]):
        grade=endpoint.get('grade')
        if grade is not None and grade not in GRADES|{'M','T'}: raise ValueError('Invalid SSL Labs grade')
        result['endpoints'].append({'address':endpoint.get('ipAddress'),'grade':grade,'status':endpoint.get('statusMessage'),
                                    'has_warnings':bool(endpoint.get('hasWarnings'))})
    return result

def collect(root=ROOT):
    config=json.loads((root/'config/sites.json').read_text());manifest(root)
    rows=[];sources=[];enabled=0;success=0
    email=os.environ.get('SSLLABS_EMAIL','').strip()
    ssl_info=None
    print('Provider terms: https://www.ssllabs.com/downloads/Qualys_SSL_Labs_Terms_of_Use.pdf')
    print('Enabled requests share target hostnames with remote provider servers. SSL Labs is permission-gated.')
    for site in config['sites']:
        host=site['host']
        if not re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}',host): raise ValueError('Invalid allowlisted host')
        row={key:site[key] for key in ['host','name','region','group']}
        row['observatory']={'state':'collection_paused','grade':None,'message':'Government assessment requests are disabled after automatic approval review. No cached-only public MDN endpoint was established; no grade is inferred.','tests':[],'history':[]}
        if site.get('observatory_enabled'):
            # Current scope intentionally only contains an operator-owned target. Extending
            # this allowlist requires explicit review; arbitrary user hostnames are not accepted.
            if site['group']!='owned' or not site.get('owner_permission'):
                raise ValueError('Government assessments remain disabled; review scope before enabling')
            enabled+=1
            raw,meta=fetch(OBS+'?'+urlencode({'host':host}),'govgrade')
            row['observatory']=normalize_observatory(json.loads(raw));row['observatory']['retrieved_at']=meta['retrieved_at'];row['observatory']['raw_sha256']=meta['sha256']
            sources.append((raw,'json',meta));success+=1
            time.sleep(1)
        row['tls']={'state':'permission_required','grade':None,'endpoints':[],
                    'message':'Public-site API use and publication require express Qualys permission plus site-owner permission. A registered SSLLABS_EMAIL secret alone is insufficient.'}
        if ssl_allowed(config,site,email):
            if ssl_info is None:
                raw,meta=fetch(SSL+'info','govgrade',{'email':email});ssl_info=json.loads(raw)
                for message in ssl_info.get('messages',[]): print('SSL Labs provider message:',message)
                sources.append((raw,'json',meta))
            raw,meta=fetch(SSL+'analyze?'+urlencode({'host':host,'fromCache':'on','all':'done'}),'govgrade',{'email':email})
            row['tls']=normalize_ssl(json.loads(raw));row['tls']['retrieved_at']=meta['retrieved_at'];row['tls']['raw_sha256']=meta['sha256'];sources.append((raw,'json',meta))
            # At most one analyze request per enabled target per run. No tight polling.
        rows.append(row)
    if enabled and not success: raise ValueError('All enabled provider requests failed')
    capture={'schema_version':1,'captured_at':utcnow(),'sites':rows,'ssl_labs_messages':(ssl_info or {}).get('messages',[])}
    summary={'tool':'govgrade','title':'Gov Grade','status':'partial','record_count':len(rows),'available_count':sum(r['observatory']['state']=='ready' for r in rows),
             'source':'MDN Observatory; permission-gated SSL Labs API v4','coverage':'One enabled owned reference, five selected government sites paused; TLS requires documented provider/publication permission.',
             'sites':[{'host':r['host'],'observatory_state':r['observatory']['state'],'grade':r['observatory'].get('grade'),'tls_state':r['tls']['state']} for r in rows]}
    save(root,capture,sources,summary)
    print(f'Saved {len(rows)} selected sites / {summary["available_count"]} MDN report(s)')

if __name__=='__main__':
    try: collect()
    except Exception as exc: raise SystemExit('Collection failed; previous published data retained: '+str(exc))
