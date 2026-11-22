import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive import manifest
from collect import ROOT, normalize_observatory, normalize_ssl, ssl_allowed

class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.report={'scan':{'id':1,'grade':'F','score':10,'algorithm_version':6,'scanned_at':'2026-11-22T00:00:00Z'},'tests':{'csp':{'title':'CSP','pass':False,'result':'missing'}},'history':[{'id':1,'grade':'F','score':10,'scanned_at':'2026-11-22T00:00:00Z'}]}
    def test_missing_is_never_a_grade(self):
        with self.assertRaises(ValueError):normalize_observatory({'scan':{}})
        bad=copy.deepcopy(self.report);bad['scan']['error']='unreachable';bad['scan']['grade']='A+'
        self.assertIsNone(normalize_observatory(bad)['grade'])
    def test_preserves_method_and_provider_time(self):
        item=normalize_observatory(self.report)
        self.assertEqual(item['algorithm_version'],6);self.assertEqual(item['scanned_at'],'2026-11-22T00:00:00Z');self.assertFalse(item['tests'][0]['pass'])
    def test_tls_requires_all_permissions_not_email_alone(self):
        site={'ssl_labs_enabled':True,'owner_permission':'owned','publication_permission':'owner grants publication'}
        self.assertFalse(ssl_allowed({},site,'registered@example.com'))
        self.assertTrue(ssl_allowed({'ssl_labs_publication_permission':'documented provider approval'},site,'registered@example.com'))
        self.assertFalse(ssl_allowed({'ssl_labs_publication_permission':'approval'},site,''))
        self.assertFalse(ssl_allowed({'ssl_labs_publication_permission':'approval'},{**site,'owner_permission':None},'registered@example.com'))
    def test_tls_never_invents_global_grade_or_pending_endpoint_grade(self):
        r=normalize_ssl({'status':'READY','endpoints':[{'ipAddress':'192.0.2.1','grade':'A'},{'ipAddress':'192.0.2.2','grade':'B'}]})
        self.assertIsNone(r['grade']);self.assertEqual([e['grade'] for e in r['endpoints']],['A','B'])
        self.assertIsNone(normalize_ssl({'status':'IN_PROGRESS'})['grade'])
    def test_deployed_config_disables_third_party_scans_and_tls(self):
        c=json.loads((ROOT/'config/sites.json').read_text())
        self.assertFalse(c['ssl_labs_publication_permission'])
        for s in c['sites']:
            if s['group']=='government':self.assertFalse(s['observatory_enabled'])
            self.assertFalse(s['ssl_labs_enabled'])
    def test_historical_tamper_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shutil.copytree(ROOT/'data',root/'data');m=manifest(root)
            path=root/'data'/m['captures'][0]['path'];path.write_text(path.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):manifest(root)
