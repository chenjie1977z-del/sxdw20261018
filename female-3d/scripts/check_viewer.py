"""Integration check: serve female-3d at localhost:8077; requires Playwright, Pillow and Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import json,math
ROOT=Path(__file__).resolve().parents[1]
results={};errors=[];requests=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 context=b.new_context(viewport={'width':1500,'height':1050},accept_downloads=True)
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:requests.append(r.url))
 page.goto('http://127.0.0.1:8077/female-3d.html',timeout=60000)
 page.wait_for_function('window.__viewer?.ready',timeout=60000)
 results['loaded']=page.locator('#loading').evaluate('(e)=>getComputedStyle(e).display')=='none'
 results['triangles']=page.evaluate('window.__viewer.triangleCount')
 for name in ['front','back','left','right','shoulder','face','neck','thighs']:
  page.locator(f'[data-view="{name}"]').click();page.wait_for_timeout(700)
  assert page.locator('#view-name').inner_text() in ['正面观察','背面观察','左侧观察','右侧观察','肩背局部观察','面部与发丝观察','锁骨与颈部观察','大腿与膝部观察']
  page.screenshot(path=str(ROOT/f'previews/v4-{name}.png'))
 results['presets']=True
 report=json.loads((ROOT/'assets/model-report.json').read_text())
 assert results['triangles']==report['total_rendered_triangles']
 names=page.evaluate('(()=>{let a=[];window.__viewer.model.traverse(o=>{if(o.isMesh)a.push(o.name)});return a})()')
 assert all(any(n.startswith(expected) for n in names) for expected in ['Eyebrows','Upper_Eyelashes','Lower_Eyelashes','Hair_Ponytail','Hair_Wispy_Bangs'])
 assert 'Hair_Bun' not in names
 results['detail_meshes']=names
 page.locator('#perspective').check()
 for view,sign in [('face',1),('neck',1),('thighs',1),('shoulder',-1)]:
  page.locator(f'[data-view="{view}"]').click()
  delta=page.evaluate('window.__viewer.camera.position.z-window.__viewer.controls.target.z')
  assert delta*sign>0,(view,delta)
 results['closeup_perspective_directions']=True
 page.locator('#perspective').uncheck()
 page.locator('#reset').click();page.wait_for_timeout(300)
 before=page.evaluate('window.__viewer.camera.position.toArray()')
 page.mouse.move(1020,450);page.mouse.down();page.mouse.move(1140,510,steps=12);page.mouse.up();page.wait_for_timeout(300)
 after=page.evaluate('window.__viewer.camera.position.toArray()');assert before!=after;results['drag_rotation']=True
 zoom=page.evaluate('window.__viewer.camera.zoom');page.mouse.wheel(0,-400);page.wait_for_timeout(400)
 assert page.evaluate('window.__viewer.camera.zoom')>zoom;results['wheel_zoom']=True
 target=page.evaluate('window.__viewer.controls.target.toArray()')
 page.mouse.move(1050,450);page.mouse.down(button='right');page.mouse.move(1120,460,steps=8);page.mouse.up(button='right');page.wait_for_timeout(250)
 assert page.evaluate('window.__viewer.controls.target.toArray()')!=target;results['pan']=True
 page.locator('[data-mode="clay"]').click();page.locator('[data-mode="skin"]').click();results['materials']=True
 page.locator('#wire').check()
 assert page.evaluate('(()=>{let a=[];window.__viewer.model.traverse(o=>{if(o.isMesh)a.push(o.material.wireframe)});return a.every(Boolean)})()')
 page.locator('#wire').uncheck();results['wireframe']=True
 page.locator('[data-view="back"]').click();page.locator('#markers').check();page.wait_for_timeout(250)
 page.wait_for_function('Array.from(document.querySelectorAll(".landmark")).some(e=>!e.hidden)',timeout=15000);page.locator('#markers').uncheck();results['markers']=True
 page.locator('#perspective').check();assert page.evaluate('window.__viewer.camera.isPerspectiveCamera');page.locator('#perspective').uncheck();results['projection_switch']=True
 page.locator('#rotate').check();before=page.evaluate('window.__viewer.camera.position.toArray()');page.wait_for_timeout(500)
 page.wait_for_function('(before)=>JSON.stringify(window.__viewer.camera.position.toArray())!==JSON.stringify(before)',arg=before,timeout=15000);page.locator('#rotate').uncheck();results['auto_rotate']=True
 page.locator('#reset').click();page.wait_for_timeout(350);page.locator('#measure').click()
 for point in [[0,1.0,.14],[.06,1.03,.14]]:
  screen=page.evaluate('(p)=>{let c=window.__viewer.camera;let v=c.position.clone().set(...p).project(c);let r=document.querySelector("canvas").getBoundingClientRect();return [r.x+(v.x*.5+.5)*r.width,r.y+(-v.y*.5+.5)*r.height]}',point)
  page.mouse.click(*screen);page.wait_for_timeout(250)
 measurement=page.locator('#measurement').inner_text();assert 'mm' in measurement,measurement;results['measurement']=measurement
 page.locator('#measure').click();page.locator('#reset').click();page.wait_for_timeout(300)
 print('CORE',json.dumps(results,ensure_ascii=False),flush=True)
 with page.expect_download(timeout=90000) as download:
  page.locator('#export').click(timeout=90000)
 download.value.save_as(str(ROOT/'previews/female-front-4K.png'))
 with Image.open(ROOT/'previews/female-front-4K.png') as image:
  assert image.width==4096;results['export_pixels']=list(image.size)
 print('EXPORT',results['export_pixels'],flush=True)
 results['page_errors']=errors;assert not errors,errors
 results['external_http_requests']=[u for u in requests if u.startswith(('http://','https://')) and not u.startswith('http://127.0.0.1:8077/')]
 assert not results['external_http_requests']
 context.close()
 offline=b.new_context(viewport={'width':1000,'height':800},offline=True)
 offline_page=offline.new_page();offline_errors=[];offline_page.on('pageerror',lambda e:offline_errors.append(str(e)))
 offline_page.set_content((ROOT/'female-3d.html').read_text(),wait_until='load',timeout=60000)
 offline_page.wait_for_function('window.__viewer?.ready',timeout=60000)
 assert not offline_errors,offline_errors
 results['offline_embedded_document']=True
 results['file_scheme']='Not tested: managed Chromium blocks file://. Same embedded document tested offline via set_content.'
 b.close()
(ROOT/'assets/browser-validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('COMPLETE',json.dumps(results,ensure_ascii=False),flush=True)
