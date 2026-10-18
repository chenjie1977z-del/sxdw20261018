"""Package the self-contained viewer without duplicating embedded model assets."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['female-3d.html','start_viewer.py','启动本地查看器.bat','启动本地查看器.command',
       '打开说明.md','Obsidian与Excalidraw教学.md','优化版03说明.md','优化版04说明.md','VALIDATION.md','THIRD_PARTY_NOTICES.md',
       'obsidian-live-embed.excalidraw',
       'previews/v4-front.png','previews/v4-back.png','previews/v4-shoulder.png','previews/v4-face.png','previews/v4-neck.png','previews/v4-thighs.png',
       'previews/teaching-viewer.png','previews/teaching-demo.excalidraw','previews/teaching-demo-4K.png',
       'assets/model-report.json','assets/gltf-validation.json','assets/browser-validation.json',
       'assets/optimization-validation.json','assets/detail-validation.json','assets/teaching-validation.json','assets/provenance.json']
FILES += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'licenses').glob('*')) if p.is_file()]
destination=ROOT.parent/'female-3d-offline.zip'
manifest={'package':'viewer and teaching tools only','revision':4,'editable_models':'Download GLB and Blender files separately from the repository.','files':[]}
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
