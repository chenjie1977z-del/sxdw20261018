"""Capture revision 06 model previews; serve this directory on localhost:8096 first."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 page=b.new_page(viewport={'width':1500,'height':1050});page.on('pageerror',lambda e:print('ERROR',e,flush=True))
 page.goto('http://127.0.0.1:8096/female-3d.html');page.wait_for_function('window.__viewer?.ready',timeout=90000)
 for view in ['face','front','back','shoulder']:
  page.evaluate('view=>window.__viewer.setView(view)',view);page.wait_for_timeout(300);page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');page.screenshot(path=str(root/f'previews/v6-{view}.png'));print('Captured',view,flush=True)
 page.evaluate('window.__viewer.setView("face");window.__viewer.camera.position.set(.55,1.54,1);window.__viewer.controls.update()');page.wait_for_timeout(300);page.screenshot(path=str(root/'previews/v6-face-three-quarter.png'))
 b.close()
