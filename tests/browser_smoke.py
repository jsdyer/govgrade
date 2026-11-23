"""CI-only Chromium checks at a GitHub Pages project subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    shots=ROOT/'browser-checks';shots.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'data/manifest.json').read_text());capture=json.loads((ROOT/'data'/manifest['captures'][-1]['path']).read_text());site_count=len(capture['sites']);available_count=sum(s['observatory']['state']=='ready' for s in capture['sites'])
    with tempfile.TemporaryDirectory() as temp:
        shutil.copytree(ROOT/'dist',Path(temp)/ROOT.name)
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temp))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch()
                page=browser.new_page(viewport={'width':1280,'height':1000})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/{ROOT.name}/')
                page.locator('#edition').filter(has_text='Captured').wait_for()
                assert page.locator('#sites button').count()==available_count
                assert page.locator('a[href*=personal-tls]').count()>=1
                page.locator('#coverage').select_option('all')
                assert page.locator('#sites button').count()==site_count
                assert 'CoolCode' in page.locator('#detail').inner_text()
                assert 'MDN Observatory' in page.locator('#detail').inner_text()
                assert 'separate from the TLS grade' in page.locator('#detail').inner_text()
                page.locator('#owned-sites').filter(has_text='hackme.ca').wait_for(state='attached')
                assert page.locator('#detail tbody tr').count()>0
                page.locator('#sites button').filter(has_text='Government of Canada').click()
                assert 'Collection paused' in page.locator('#detail').inner_text()
                assert 'not included in the personal checker' in page.locator('#detail').inner_text()
                page.locator('#search').fill('<img src=x onerror=alert(1)>')
                assert page.locator('#sites button').count()==0
                assert page.locator('img').count()==0
                page.locator('#search').fill('')
                page.locator('#coverage').select_option('available')
                assert page.locator('#sites button').count()==available_count
                with page.expect_download() as event: page.locator('#export').click()
                assert event.value.suggested_filename=='govgrade-reports.csv'
                page.locator('summary').filter(has_text='Compare a report').click()
                payload={'scan':{'grade':'A','score':90,'algorithm_version':6,'scanned_at':'2026-11-22T00:00:00Z'},'tests':{'test':{'title':'<img src=x onerror=alert(1)>','pass':False,'result':'literal text'}}}
                page.locator('#import').set_input_files({'name':'report.json','mimeType':'application/json','buffer':json.dumps(payload).encode()})
                page.locator('#import-status').filter(has_text='Loaded into this tab').wait_for()
                assert 'unverified' in page.locator('#import-status').inner_text()
                assert '<img src=x' in page.locator('#detail').inner_text()
                assert page.locator('img').count()==0
                page.locator('#capture').dispatch_event('change')
                page.locator('#detail tbody tr').first.wait_for()
                page.locator('#coverage').select_option('all')

                page.screenshot(path=str(shots/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal mobile overflow'
                page.screenshot(path=str(shots/'mobile.png'),full_page=True)
                assert not errors,errors
                browser.close()
        finally: server.shutdown()
    print('Browser checks passed: subpath, real data, filters, export, safe text, desktop and mobile')
if __name__=='__main__':main()
