"""Revision 6 integration: serve female-3d on localhost:8096; Playwright + Pillow."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import json,hashlib

ROOT=Path(__file__).resolve().parents[1]
report={'revision':6,'glb_sha256':hashlib.sha256((ROOT/'assets/asian-female.glb').read_bytes()).hexdigest(),'html_sha256':hashlib.sha256((ROOT/'female-3d.html').read_bytes()).hexdigest()};errors=[];requests=[]
for asset in json.loads((ROOT/'assets/provenance.json').read_text())['assets']:
    assert hashlib.sha256((ROOT/asset['path']).read_bytes()).hexdigest()==asset['sha256']
report['source_assets_verified']=True
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1500,'height':1050},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
    def load():
        page.goto('http://127.0.0.1:8096/female-3d.html');page.wait_for_function('window.__viewer?.ready',timeout=90000)
        page.evaluate('window.__viewer.renderer.setPixelRatio(.5)')
    def project(point):
        return page.evaluate('''p=>{const v=window.__viewer;v.camera.updateMatrixWorld();const c=v.camera.position.clone().set(...p).project(v.camera),r=v.renderer.domElement.getBoundingClientRect();return [r.x+(c.x*.5+.5)*r.width,r.y+(-c.y*.5+.5)*r.height]}''',point)
    def click_world(point):page.mouse.click(*project(point))
    def count():return page.evaluate('window.__viewer.anchors.annotations.length')
    def state():return page.evaluate('window.__viewer.anchors.project()')
    def field(selector,value):page.locator(selector).evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("change",{bubbles:true}))}',str(value))
    def drag_pixels(start,delta):
        page.mouse.move(*start);page.mouse.down();page.mouse.move(start[0]+delta[0],start[1]+delta[1],steps=6);page.mouse.up()
    load();report['model_key']=page.evaluate('window.__viewer.anchors.modelKey');report['triangles']=page.evaluate('window.__viewer.triangleCount')
    assert report['triangles']==json.loads((ROOT/'assets/model-report.json').read_text())['total_rendered_triangles']
    names=page.evaluate('(()=>{let a=[];window.__viewer.model.traverse(o=>{if(o.isMesh)a.push(o.name)});return a})()')
    assert not any(x in names for x in ['Hair_Ponytail','Hair_Wispy_Bangs','Hair_Bun']);report['no_bangs_or_ponytail']=True
    previous=json.loads((ROOT/'previews/v5-surface-lesson.json').read_text())
    assert page.evaluate('v=>window.__viewer.anchors.importProject(v)',previous)==len(previous['annotations'])
    assert [m['anchors'] for m in state()['annotations']]==[m['anchors'] for m in previous['annotations']]
    page.locator('#anchor-clear').click();report['verified_v5_lesson_compatibility']=True
    # New shapes are created by real pointer clicks on the surface.
    page.evaluate('window.__viewer.setView("abdomen")')
    specs=[('point',[[0,1.0,.14]]),('line',[[-.045,1.09,.14],[.045,1.09,.14]]),('circle',[[0,1.05,.14],[.025,1.05,.14]]),('triangle',[[-.035,1.14,.14],[.035,1.14,.14],[0,1.18,.14]]),('rectangle',[[-.04,1.01,.14],[.04,1.04,.14]])]
    for number,(kind,points) in enumerate(specs,1):
        page.locator('[data-anchor-tool="'+kind+'"]').click();page.locator('#anchor-text').fill('')
        for point in points:click_world(point)
        assert count()==number,(kind,state())
        assert state()['annotations'][-1]['kind']==kind
    report['point_line_circle_triangle_rectangle_pointer_creation']=True
    circle=state()['annotations'][2];page.locator('#anchor-list').select_option(circle['id'])
    endpoint=page.evaluate('window.__viewer.anchors.pointFromAnchor(window.__viewer.anchors.annotations[2].anchors[1]).point.toArray()')
    before=state()['annotations'][2]['anchors'];drag_pixels(project(endpoint),[22,-6]);assert state()['annotations'][2]['anchors']!=before
    report['circle_radius_handle_edit']=True
    rect_id=state()['annotations'][4]['id'];page.locator('#anchor-list').select_option(rect_id)
    before=state()['annotations'][4]['anchors'];page.locator('#anchor-grow').click();assert state()['annotations'][4]['anchors']!=before
    report['rectangle_resize']=True
    original=state()['annotations'];page.locator('[data-anchor-tool="rotate"]').click();drag_pixels([1150,400],[70,20]);assert state()['annotations']==original
    page.evaluate('window.__viewer.setView("abdomen")')
    report['new_shapes_keep_anchors_on_rotation']=True
    # Empty viewer menu and right-button panning coexist.
    page.mouse.click(1250,350,button='right');assert page.locator('#viewer-context').is_visible()
    page.screenshot(path=str(ROOT/'previews/v6-view-context.png'))
    assert page.locator('#viewer-context').get_by_role('menuitem',name='添加圆',exact=True).count()==1
    page.keyboard.press('Escape');assert page.locator('#viewer-context').is_hidden()
    target=page.evaluate('window.__viewer.controls.target.toArray()');page.mouse.move(1200,400);page.mouse.down(button='right');page.mouse.move(1230,410,steps=4);page.mouse.up(button='right')
    assert page.evaluate('window.__viewer.controls.target.toArray()')!=target
    assert page.locator('#viewer-context').is_hidden();report['context_menu_and_right_drag_pan']=True
    page.evaluate('window.__viewer.setView("abdomen")')
    # Right-click an existing shape even in rotation mode; rename using a dialog.
    point=page.evaluate('window.__viewer.anchors.pointFromAnchor(window.__viewer.anchors.annotations[0].anchors[0]).point.toArray()')
    print('Point context pixels',project(point),'world',point,flush=True)
    page.mouse.click(*project(point),button='right');assert page.locator('#viewer-context').is_visible()
    page.screenshot(path=str(ROOT/'previews/v6-annotation-context.png'))
    page.locator('#viewer-context').get_by_role('menuitem',name='重命名 / 修改文字',exact=True).click()
    assert page.locator('#rename-dialog').is_visible();page.locator('#rename-value').fill('腹部定位点');page.locator('#rename-form button[type="submit"]').click()
    assert state()['annotations'][0]['text']=='腹部定位点';report['annotation_context_rename']=True
    # Resize a text box by its screen-facing corner, then edit width, height and font.
    page.locator('#anchor-list').select_option(state()['annotations'][0]['id'])
    page.evaluate('window.__viewer.anchors.update()')
    handle=page.evaluate('(()=>{let p;window.__viewer.anchors.root.traverse(o=>{if(o.userData.resize&&o.userData.id===window.__viewer.anchors.selected)p=o.position.toArray()});return p})()')
    before=state()['annotations'][0];drag_pixels(project(handle),[25,18]);after=state()['annotations'][0]
    assert after['labelWidth']>before['labelWidth'] and after['labelHeight']>before['labelHeight'],(before,after)
    field('#anchor-label-width',245);field('#anchor-label-height',96);field('#anchor-font',1.3)
    m=state()['annotations'][0];assert (m['labelWidth'],m['labelHeight'],m['fontSize'])==(245,96,1.3)
    assert state()['annotations'][0]['anchors']==before['anchors'];report['text_box_corner_resize_width_height_font']=True
    page.mouse.click(*project(point),button='right');page.locator('#viewer-context').get_by_role('menuitem',name='删除标注',exact=True).click();assert count()==4
    page.locator('#anchor-undo').click();assert count()==5 and state()['annotations'][0]['text']=='腹部定位点';report['annotation_context_delete_undo']=True
    with page.expect_download(timeout=60000) as download:page.locator('#anchor-save').click()
    shapes_file=ROOT/'previews/v6-shapes-lesson.json';download.value.save_as(str(shapes_file));shapes=json.loads(shapes_file.read_text())
    page.locator('#anchor-clear').click();page.locator('#anchor-file').set_input_files(str(shapes_file));page.wait_for_function('window.__viewer.anchors.annotations.length===5')
    assert [(m['kind'],m['anchors']) for m in state()['annotations']]==[(m['kind'],m['anchors']) for m in shapes['annotations']]
    report['new_shapes_serialization_restore']=True
    wrong=json.loads(shapes_file.read_text());wrong['annotations'][0]['labelWidth']=50000
    assert page.evaluate('v=>{try{window.__viewer.anchors.importProject(v);return false}catch(e){return true}}',wrong) and count()==5
    wrong=json.loads(shapes_file.read_text());wrong['annotations'][2]['frame']=[[1,0,0],[1,0,0]]
    assert page.evaluate('v=>{try{window.__viewer.anchors.importProject(v);return false}catch(e){return true}}',wrong) and count()==5
    report['new_shape_invalid_import_is_atomic']=True
    page.locator('button[data-theme="slate"]').click();page.locator('[data-anchor-tool="select"]').click();page.locator('#anchor-list').select_option(state()['annotations'][0]['id'])
    page.evaluate('window.__viewer.renderer.setPixelRatio(1)');page.locator('aside').evaluate('(e)=>e.scrollTop=0');page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');page.screenshot(path=str(ROOT/'previews/v6-shape-tools.png'));page.evaluate('window.__viewer.renderer.setPixelRatio(.5)')
    page.locator('#anchor-clear').click();page.locator('button[data-theme="ivory"]').click();page.evaluate('window.__viewer.setView("front")')
    field('#anchor-size',1);page.locator('#anchor-text').fill('')
    print('New shape tools, menus, text resize and JSON restore passed',flush=True)
    # Real pointer creation and dragging, not just injecting marks into the scene.
    page.locator('#anchor-text').fill('锁骨区 · 示意');page.locator('[data-anchor-tool="label"]').click();click_world([.045,1.35,.09]);assert count()==1
    first=state()['annotations'][0];report['pointer_surface_anchor']=True;print('Created surface label',flush=True)
    page.locator('[data-anchor-tool="select"]').click()
    label=page.evaluate('(()=>{let p;window.__viewer.anchors.root.traverse(o=>{if(o.userData.label)p=o.position.toArray()});return p})()')
    before=state()['annotations'][0]['labelOffset'];drag_pixels(project(label),[35,-20]);assert state()['annotations'][0]['labelOffset']!=before
    report['label_drag']=True
    field('#anchor-size',1.7);assert abs(state()['annotations'][0]['size']-1.7)<1e-6;report['resize']=True
    page.locator('[data-anchor-tool="curve"]').click();page.locator('#anchor-text').fill('两点等分线');click_world([-.055,1.28,.12]);click_world([.055,1.28,.12]);assert count()==2
    curve_id=state()['annotations'][1]['id'];field('#anchor-bend',.32);page.locator('#anchor-ticks').check();field('#anchor-divisions',8);page.locator('#anchor-arrow').check()
    curve=state()['annotations'][1];assert curve['bend']==.32 and curve['ticks'] and curve['divisions']==8 and curve['arrow'];report['curve_and_ticks']=True;print('Created editable curve and 8 divisions',flush=True)
    children=page.evaluate('(id)=>window.__viewer.anchors.root.children.find(g=>g.name==="Annotation_"+id).children.length',curve_id);assert children>16
    page.locator('[data-anchor-tool="select"]').click()
    label=page.evaluate('(id)=>window.__viewer.anchors.root.children.find(g=>g.name==="Annotation_"+id).children.find(o=>o.userData.label).position.toArray()',curve_id)
    before=state()['annotations'][1]['anchors'];page.keyboard.down('Shift');drag_pixels(project(label),[12,-8]);page.keyboard.up('Shift');assert state()['annotations'][1]['anchors']!=before;report['whole_annotation_drag']=True
    endpoint=page.evaluate('window.__viewer.anchors.pointFromAnchor(window.__viewer.anchors.annotations[1].anchors[1]).point.toArray()')
    before=state()['annotations'][1]['anchors'][1];drag_pixels(project(endpoint),[15,12]);assert state()['annotations'][1]['anchors'][1]!=before;report['endpoint_reanchor']=True
    before=state()['annotations'][1]['anchors'];page.locator('#anchor-grow').click();assert state()['annotations'][1]['anchors']!=before;report['shape_resize']=True
    page.locator('[data-anchor-tool="pen"]').click();page.locator('#anchor-text').fill('')
    start=project([-.035,1.03,.14]);end=project([.035,1.03,.14]);drag_pixels(start,[end[0]-start[0],end[1]-start[1]]);assert count()==3
    assert state()['annotations'][2]['kind']=='pen' and len(state()['annotations'][2]['anchors'])>2
    page.locator('#anchor-closed').check();assert state()['annotations'][2]['closed'];report['surface_pen_and_closed_region']=True
    page.locator('#anchor-delete').click();assert count()==2;page.locator('#anchor-undo').click();assert count()==3;page.locator('#anchor-redo').click();assert count()==2;page.locator('#anchor-undo').click();assert count()==3
    report['undo_redo']=True;print('Dragging, resizing, pen and undo passed',flush=True)
    anchored=state()['annotations'];page.locator('[data-anchor-tool="rotate"]').click()
    zoom=page.evaluate('window.__viewer.camera.zoom');page.mouse.move(1100,430);page.mouse.wheel(0,-250);page.wait_for_function('(z)=>window.__viewer.camera.zoom>z',arg=zoom);report['wheel_zoom']=True
    center=page.evaluate('window.__viewer.controls.target.toArray()');page.mouse.move(1100,430);page.mouse.down(button='right');page.mouse.move(1120,440,steps=4);page.mouse.up(button='right');page.wait_for_function('(c)=>JSON.stringify(window.__viewer.controls.target.toArray())!==JSON.stringify(c)',arg=center);report['right_pan']=True
    page.evaluate('window.__viewer.setView("front")')
    pos=page.evaluate('window.__viewer.camera.position.toArray()');drag_pixels([1100,430],[80,30]);page.wait_for_function('(p)=>JSON.stringify(window.__viewer.camera.position.toArray())!==JSON.stringify(p)',arg=pos)
    assert state()['annotations']==anchored;report['rotation_preserves_anchors']=True
    page.evaluate('window.__viewer.setView("back")');page.wait_for_function('window.__viewer.anchors.root.children.filter(g=>g.name.startsWith("Annotation_")).every(g=>!g.visible)',timeout=30000)
    report['backside_occlusion']=True
    page.evaluate('window.__viewer.setView("front")');page.wait_for_function('window.__viewer.anchors.root.children.filter(g=>g.name.startsWith("Annotation_")).every(g=>g.visible)',timeout=30000)
    light=page.evaluate('window.__viewer.scene.children.filter(o=>o.isLight).map(o=>o.intensity)')
    for theme in ['ivory','slate','mist']:
        page.locator('button[data-theme="'+theme+'"]').click();assert page.evaluate('window.__viewer.theme')==theme
        assert light==page.evaluate('window.__viewer.scene.children.filter(o=>o.isLight).map(o=>o.intensity)')
        page.evaluate('window.__viewer.renderer.setPixelRatio(1)');page.locator('aside').evaluate('(e)=>e.scrollTop=0');page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');page.screenshot(path=str(ROOT/f'previews/v6-anchors-{theme}.png'));page.evaluate('window.__viewer.renderer.setPixelRatio(.5)')
    report['themes_without_light_changes']=True;print('Rotation, occlusion and all three themes passed',flush=True)
    page.locator('#markers').check();assert page.locator('.landmark').first.evaluate('(e)=>getComputedStyle(e).color')=='rgb(32, 59, 60)';page.locator('#markers').uncheck();report['dark_marker_text_contrast']=True
    page.evaluate('(()=>{let o=window.__viewer.model.getObjectByName("Female_Surface");window.originalSurface={m:o.material,map:o.material.map,normal:o.material.normalMap}})()')
    page.locator('[data-mode="clay"]').click();assert page.evaluate('!originalSurface.m.normalMap');page.locator('[data-mode="skin"]').click();assert page.evaluate('originalSurface.m.map===originalSurface.map && originalSurface.m.normalMap===originalSurface.normal');report['skin_clay_restore']=True
    page.locator('#measure').click();click_world([0,1.0,.14]);click_world([.06,1.03,.14]);assert 'mm' in page.locator('#measurement').inner_text();page.locator('#measure').click();report['two_point_measurement']=True
    page.locator('#perspective').check();page.wait_for_timeout(300);assert state()['annotations']==anchored;page.locator('#perspective').uncheck();report['projection_preserves_anchors']=True
    with page.expect_download(timeout=60000) as download:page.locator('#anchor-save').click()
    saved=ROOT/'previews/v6-surface-lesson.json';download.value.save_as(str(saved));lesson=json.loads(saved.read_text());assert len(lesson['annotations'])==3
    wrong=json.loads(saved.read_text());wrong['modelKey']='wrong-model';before=count()
    rejected=page.evaluate('value=>{try{window.__viewer.anchors.importProject(value);return false}catch(e){return true}}',wrong);assert rejected and count()==before
    wrong=json.loads(saved.read_text());wrong['annotations'][0]['anchors'][0]['face']=99999999
    assert page.evaluate('v=>{try{window.__viewer.anchors.importProject(v);return false}catch(e){return true}}',wrong) and count()==before
    report['invalid_import_is_atomic']=True
    page.locator('#anchor-clear').click();assert count()==0;page.locator('#anchor-undo').click();assert count()==3
    load();page.locator('#anchor-file').set_input_files(str(saved));page.wait_for_function('window.__viewer.anchors.annotations.length===3');assert page.evaluate('window.__viewer.anchors.modelKey')==report['model_key']
    restored=state()['annotations'];assert [a['anchors'] for a in restored]==[a['anchors'] for a in lesson['annotations']];report['save_reload_restore']=True
    page.locator('#anchor-file').set_input_files(str(saved));page.wait_for_function('window.__viewer.anchors.annotations.length===6');assert len(set(m['id'] for m in state()['annotations']))==6;report['import_merges_new_ids']=True
    selected_id=state()['annotations'][0]['id'];page.locator('#anchor-list').select_option(selected_id);assert page.evaluate('window.__viewer.anchors.selected')==selected_id;old_text=state()['annotations'][0]['text'];page.locator('#anchor-text').fill('长文字可分行显示并保持清晰'*4);page.locator('#anchor-text').dispatch_event('change')
    assert page.evaluate('(()=>{let s;window.__viewer.anchors.root.traverse(o=>{if(o.userData.label&&o.userData.id===window.__viewer.anchors.selected)s=o});return s.userData.lines>1})()');page.locator('#anchor-text').fill(old_text);page.locator('#anchor-text').dispatch_event('change');report['multiline_labels']=True
    page.locator('#anchor-clear').click();page.locator('#anchor-file').set_input_files(str(saved));page.wait_for_function('window.__viewer.anchors.annotations.length===3')
    page.locator('button[data-theme="slate"]').click()
    with page.expect_download(timeout=90000) as download:page.locator('#export').click(timeout=90000)
    download.value.save_as(str(ROOT/'previews/v6-anchored-4K.png'))
    with Image.open(ROOT/'previews/v6-anchored-4K.png') as im:assert im.width==4096;report['export_pixels']=list(im.size)
    page.locator('#annotate-view').click(timeout=90000);page.wait_for_function('window.__viewer.teaching.active',timeout=90000);assert page.locator('#anchor-panel').is_hidden()
    page.locator('#annotation-text').fill('固定视角板书 · 示例');page.locator('[data-annotation-tool="text"]').click();page.locator('#annotation-canvas').click(position={'x':100,'y':150})
    page.locator('[data-annotation-tool="arrow"]').click();box=page.locator('#annotation-canvas').bounding_box();drag_pixels([box['x']+320,box['y']+200],[120,100]);assert page.evaluate('window.__viewer.teaching.currentBoard.marks.length')==2
    page.locator('aside').evaluate('(e)=>e.scrollTop=0');page.screenshot(path=str(ROOT/'previews/teaching-viewer.png'))
    with page.expect_download(timeout=90000) as download:page.locator('#export-excalidraw').click()
    download.value.save_as(str(ROOT/'previews/teaching-demo.excalidraw'));exc=json.loads((ROOT/'previews/teaching-demo.excalidraw').read_text());assert {e['type'] for e in exc['elements']}=={'image','arrow','text'}
    with page.expect_download(timeout=90000) as download:page.locator('#export-marked').click()
    download.value.save_as(str(ROOT/'previews/teaching-demo-4K.png'));report['fixed_view_excalidraw_export']=True
    page.locator('#return-3d').click();assert page.locator('#anchor-panel').is_visible();assert count()==3 and page.evaluate('window.__viewer.controls.enabled');report['fixed_view_and_3d_coexist']=True
    report['page_errors']=errors;assert not errors,errors
    report['external_requests']=[r for r in requests if r.startswith(('http:','https:')) and not r.startswith('http://127.0.0.1:8096/')];assert not report['external_requests']
    page.close();offline=browser.new_context(offline=True,viewport={'width':1000,'height':800});op=offline.new_page();op.on('pageerror',lambda e:errors.append(str(e)));op.set_content((ROOT/'female-3d.html').read_text(),wait_until='load',timeout=90000);op.wait_for_function('window.__viewer?.ready',timeout=90000)
    assert op.evaluate('window.__viewer.anchors.modelKey')==report['model_key'];assert op.evaluate('v=>window.__viewer.anchors.importProject(v)',lesson)==3;report['offline_embedded_restore']=True;report['page_errors']=errors;assert not errors,errors
    browser.close()
(ROOT/'assets/tools-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True)
