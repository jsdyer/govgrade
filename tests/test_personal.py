import unittest,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ssl_personal
class PersonalTests(unittest.TestCase):
 def test_target_is_owned(self):
  self.assertEqual(ssl_personal.check_host('coolcode.ca'),'coolcode.ca')
  self.assertEqual(ssl_personal.check_host('hackme.ca'),'hackme.ca')
  for host in ['https://hackme.ca/','hackme.ca.evil.example','127.0.0.1','localhost']:
   with self.assertRaises(ValueError):ssl_personal.check_host(host)
  with self.assertRaises(ValueError):ssl_personal.check_host('www.canada.ca')
 def test_info_precedes_scan_and_ci_summary_contains_no_api_payload(self):
  with tempfile.TemporaryDirectory() as d:
   summary=Path(d)/'summary.md'
   with patch.dict('os.environ',{'SSLLABS_EMAIL':'private@example.org','GITHUB_STEP_SUMMARY':str(summary)}),patch.object(ssl_personal,'call',side_effect=[{'engineVersion':'test','messages':['provider notice']},{'status':'READY','sensitive':'PRIVATE_REPORT'}]) as request:
    ssl_personal.run('coolcode.ca',True)
   self.assertEqual(request.call_args_list[0].args[0],'info')
   self.assertIn('host=coolcode.ca',request.call_args_list[1].args[0]);self.assertNotIn('startNew',request.call_args_list[1].args[0])
   text=summary.read_text();self.assertIn('ssllabs.com/ssltest/',text);self.assertNotIn('PRIVATE_REPORT',text);self.assertNotIn('private@example.org',text)
 def test_pending_assessment_returns_link_without_claiming_completion(self):
  with tempfile.TemporaryDirectory() as d:
   summary=Path(d)/'summary.md'
   with patch.dict('os.environ',{'SSLLABS_EMAIL':'private@example.org','GITHUB_STEP_SUMMARY':str(summary)}),patch.object(ssl_personal,'call',side_effect=[{'engineVersion':'test'},{'status':'IN_PROGRESS'}]),patch.object(ssl_personal.time,'monotonic',side_effect=[0,61]):
    state=ssl_personal.run('coolcode.ca',True,60)
   self.assertEqual(state,'IN_PROGRESS');text=summary.read_text();self.assertIn('still processing',text);self.assertIn('ssllabs.com/ssltest/',text);self.assertNotIn('check completed',text)
 def test_provider_error_remains_failure(self):
  with patch.dict('os.environ',{'SSLLABS_EMAIL':'private@example.org'}),patch.object(ssl_personal,'call',side_effect=[{'engineVersion':'test'},{'status':'ERROR'}]):
   with self.assertRaises(RuntimeError):ssl_personal.run('coolcode.ca',True,60)
