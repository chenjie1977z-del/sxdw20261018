"""Revision 4 model/material/teaching integration. Serve this folder on :8077."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import hashlib,json,struct

ROOT=Path(__file__).resolve().parents[1]
binary=(ROOT/'assets/asian-female.glb').read_bytes()
length=struct.unpack_from('<I',binary,12)[0];gltf=json.loads(binary[20:20+length])
report={'revision':4,'glb_sha256':hashlib.sha256(binary).hexdigest()}
report['meshes']=[m['name'] for m in gltf['meshes']]
report['mesh_nodes']=[n['name'] for n in gltf['nodes'] if 'mesh' in n]
assert len(report['meshes'])==9
assert 'Hair_Bun' not in report['meshes']
assert all(not any(k in m['name'] for k in ['Bra','Shorts','Straps']) for m in gltf['meshes'])
surface=gltf['meshes'][next(n['mesh'] for n in gltf['nodes'] if n['name']=='Female_Surface')]
assert all('TANGENT' in p['attributes'] for p in surface['primitives'])
provenance=json.loads((ROOT/'assets/provenance.json').read_text())
for source in provenance['assets']:
    assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256']
report['source_asset_hashes_checked']=len(provenance['assets'])
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1500,'height':1050},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8077/female-3d.html');page.wait_for_function('window.__viewer?.ready',timeout=60000)
    report['iris_factor']=page.evaluate('window.__viewer.model.getObjectByName("Eyes_2").material.color.toArray()')
    assert all(abs(a-b)<1e-6 for a,b in zip(report['iris_factor'],[.2,.4,.3]))
    page.locator('[data-view="face"]').click();page.screenshot(path=str(ROOT/'previews/v4-face.png'))
    report['materials']=page.evaluate('''()=>{let m;window.__viewer.model.traverse(o=>{if(o.name==='Female_Surface')m=o.material});window.surfaceMaterial=m;window.originalMaps={map:m.map,normalMap:m.normalMap};return {albedo:[m.map.image.width,m.map.image.height],normal:[m.normalMap.image.width,m.normalMap.image.height]}}''')
    assert report['materials']=={'albedo':[4096,4096],'normal':[4096,4096]}
    page.locator('[data-mode="clay"]').click()
    assert page.evaluate('!surfaceMaterial.normalMap && surfaceMaterial.map!==originalMaps.map')
    page.locator('[data-mode="skin"]').click()
    assert page.evaluate('surfaceMaterial.map===originalMaps.map && surfaceMaterial.normalMap===originalMaps.normalMap')
    report['clay_skin_map_restoration']=True
    page.locator('[data-view="shoulder"]').click()
    page.locator('#annotate-view').click(timeout=90000);page.wait_for_function('window.__viewer.teaching.active',timeout=90000)
    assert not page.evaluate('window.__viewer.controls.enabled')
    page.locator('[data-annotation-tool="arrow"]').click()
    box=page.locator('#annotation-canvas').bounding_box()
    page.mouse.move(box['x']+280,box['y']+280);page.mouse.down();page.mouse.move(box['x']+620,box['y']+470,steps=10);page.mouse.up()
    page.locator('#annotation-text').fill('肩背体表观察 · 示意')
    page.locator('[data-annotation-tool="text"]').click();page.locator('#annotation-canvas').click(position={'x':250,'y':200})
    assert page.evaluate('window.__viewer.teaching.currentBoard.marks.length')==2
    page.locator('#undo-mark').click();assert page.evaluate('window.__viewer.teaching.currentBoard.marks.length')==1
    page.locator('#redo-mark').click();assert page.evaluate('window.__viewer.teaching.currentBoard.marks.length')==2
    page.locator('aside').evaluate('(e)=>e.scrollTop=0');page.screenshot(path=str(ROOT/'previews/teaching-viewer.png'))
    with page.expect_download(timeout=90000) as download:page.locator('#export-excalidraw').click()
    download.value.save_as(str(ROOT/'previews/teaching-demo.excalidraw'))
    exported=json.loads((ROOT/'previews/teaching-demo.excalidraw').read_text())
    assert {e['type'] for e in exported['elements']}=={'image','arrow','text'}
    assert len(exported['files'])==1
    report['excalidraw_types']=[e['type'] for e in exported['elements']]
    with page.expect_download(timeout=90000) as download:page.locator('#export-marked').click()
    download.value.save_as(str(ROOT/'previews/teaching-demo-4K.png'))
    with Image.open(ROOT/'previews/teaching-demo-4K.png') as image:
        assert image.width==4096;report['marked_export_pixels']=list(image.size)
    page.locator('#return-3d').click();assert page.evaluate('window.__viewer.controls.enabled')
    report['teaching_annotation_and_return']=True
    report['page_errors']=errors;assert not errors,errors
    browser.close()
(ROOT/'assets/detail-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False),flush=True)
