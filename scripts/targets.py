"""Validate the explicit site list before any provider request."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read_config(root=ROOT):
    config=json.loads((root/'config/sites.json').read_text())
    rows=config.get('sites',[])
    if not 1<=len(rows)<=30 or len({s['host'] for s in rows})!=len(rows):raise ValueError('Configure one to thirty distinct sites')
    for site in rows:
        if not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}',site['host']):raise ValueError('Invalid allowlisted hostname')
        if site.get('observatory_enabled') and (site.get('group')!='owned' or not site.get('owner_permission')):
            raise ValueError('Only explicitly authorized owned sites can be enabled')
    return config

def config_hash(root=ROOT):
    return hashlib.sha256(json.dumps(read_config(root),sort_keys=True).encode()).hexdigest()

def needs_refresh(root=ROOT):
    path=root/'data/index.json'
    return not path.exists() or json.loads(path.read_text()).get('config_sha256')!=config_hash(root)

def owned_hosts(root=ROOT):
    return [s['host'] for s in read_config(root)['sites'] if s['group']=='owned' and s.get('owner_permission')]
