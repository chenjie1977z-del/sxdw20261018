"""Package the self-contained viewer without duplicating embedded model assets."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['female-3d.html','start_viewer.py','启动本地查看器.bat','启动本地查看器.command',
       '打开说明.md','Obsidian与Excalidraw教学.md','优化版03说明.md','优化版04说明.md','三维标注与优化版05.md','图形工具与优化版06.md','VALIDATION.md','THIRD_PARTY_NOTICES.md',
       'obsidian-live-embed.excalidraw',
       'previews/v5-front.png','previews/v5-back.png','previews/v5-shoulder.png','previews/v5-face.png','previews/v5-neck.png','previews/v5-thighs.png',
       'previews/v5-anchors-ivory.png','previews/v5-anchors-slate.png','previews/v5-anchors-mist.png',
       'previews/v5-hairline-back.png','previews/v5-abdomen.png','previews/v5-kneeback.png','previews/v5-wrist.png','previews/v5-surface-lesson.json','previews/v5-anchored-4K.png',
       'previews/teaching-viewer.png','previews/teaching-demo.excalidraw','previews/teaching-demo-4K.png',
       'assets/model-report.json','assets/gltf-validation.json','assets/browser-validation.json',
       'assets/optimization-validation.json','assets/detail-validation.json','assets/anchor-validation.json','assets/teaching-validation.json','assets/provenance.json']
FILES += ['assets/tools-validation.json','assets/anchor-compatibility.json']
FILES += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'previews').glob('v6-*')) if p.is_file()]
FILES += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'licenses').glob('*')) if p.is_file()]
# Refuse stale reports when a model or the bundled viewer changed after testing.
validation=json.loads((ROOT/'assets/tools-validation.json').read_text())
for key,name in [('html_sha256','female-3d.html'),('glb_sha256','assets/asian-female.glb')]:
    assert validation[key]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),f'Rerun check_tools.py for {name}'
assert not validation['page_errors'] and not validation['external_requests']
assert validation['triangles']==json.loads((ROOT/'assets/model-report.json').read_text())['total_rendered_triangles']
assert json.loads((ROOT/'assets/anchor-compatibility.json').read_text())['current_glb_sha256']==validation['glb_sha256']
destination=ROOT.parent/'female-3d-offline.zip'
manifest={'package':'viewer and teaching tools only','revision':6,'editable_models':'Download GLB and Blender files separately from the repository.','files':[]}
with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name in FILES:
        p=ROOT/name
        assert p.is_file(),p
        archive.write(p,Path('female-3d')/name)
        manifest['files'].append({'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    archive.writestr('female-3d/package-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    assert archive.read('female-3d/female-3d.html')==(ROOT/'female-3d.html').read_bytes()
print('Verified offline ZIP:',destination.stat().st_size,'bytes;',len(FILES),'files plus manifest')
