"""Personal noncommercial SSL Labs client for the operator-owned CoolCode site."""
import argparse,json,os,time,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlencode
BASE='https://api.ssllabs.com/api/v4/'
TERMS='https://www.ssllabs.com/downloads/Qualys_SSL_Labs_Terms_of_Use.pdf'

def call(path,email):
    req=urllib.request.Request(BASE+path,headers={'email':email,'User-Agent':'CoolCode Personal TLS Client/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:return json.loads(r.read(10_000_000))
    except urllib.error.HTTPError as e:raise RuntimeError('SSL Labs HTTP '+str(e.code)+'; check registration for 441, or retry later for rate/service errors.') from None
    except (OSError,ValueError):raise RuntimeError('SSL Labs unavailable or returned invalid JSON. Try again later.') from None

def check_host(host):
    if host!='coolcode.ca':raise ValueError('This personal workflow is authorized only for coolcode.ca')
    return host

def run(host,links_only=False):
    check_host(host)
    email=os.environ.get('SSLLABS_EMAIL','').strip()
    if not email:raise ValueError('Set SSLLABS_EMAIL to the successfully registered email address')
    print('Terms: '+TERMS)
    print('This personal client sends the owned hostname to remote Qualys servers; a cache miss can initiate an assessment.')
    info=call('info',email)
    for message in info.get('messages',[]):print('SSL Labs message:',str(message))
    if not info.get('engineVersion'):raise ValueError('Invalid SSL Labs availability response')
    path='analyze?'+urlencode({'host':host,'fromCache':'on','all':'done','maxAge':'24','publish':'off'})
    deadline=time.monotonic()+600
    while True:
        result=call(path,email)
        if result.get('status')=='READY':break
        if result.get('status')=='ERROR':raise RuntimeError('SSL Labs could not assess this host; inspect its report')
        if result.get('status') not in ('DNS','IN_PROGRESS'):raise ValueError('Unexpected assessment state')
        if time.monotonic()>=deadline:raise RuntimeError('Assessment still in progress; open the provider report later')
        print('Assessment in progress; waiting 20 seconds.');time.sleep(20)
    link='https://www.ssllabs.com/ssltest/analyze.html?d='+host
    text='# Personal TLS check completed\n\n[Open your SSL Labs report]('+link+')\n\nThe registered email worked. The complete report remains at SSL Labs. No API report is committed or republished by this workflow.\n'
    print(text)
    if not links_only:print(json.dumps(result,indent=2))
    if os.getenv('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(text)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--host',default='coolcode.ca');parser.add_argument('--links-only',action='store_true');args=parser.parse_args()
    try:run(args.host,args.links_only)
    except Exception as e:raise SystemExit(str(e)) from None
