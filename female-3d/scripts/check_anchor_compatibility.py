"""Verify triangle/corner correspondence before allowing a known previous lesson key.

Usage: python scripts/check_anchor_compatibility.py /path/to/previous.glb
UVs are compared at every triangle corner (not just vertex/index counts).
"""
from pathlib import Path
import sys,json,struct,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def read(path):
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
    primitive=doc['meshes'][next(n for n in doc['nodes'] if n['name']=='Female_Surface')['mesh']]['primitives'][0]
    def attr(i):
        a=doc['accessors'][i];view=doc['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        assert 'byteStride' not in view,'Interleaved attributes require a strided reader'
        return np.frombuffer(binary,dtype=dtype,count=a['count']*components,offset=view.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],components)
    index=attr(primitive['indices']).ravel();pos=attr(primitive['attributes']['POSITION']);uv=attr(primitive['attributes']['TEXCOORD_0'])
    fnv=2166136261
    for value in pos.tobytes()+index.tobytes():fnv=((fnv^value)*16777619)&0xffffffff
    return {'key':f'female-surface-{len(pos)}-{len(index)}-{fnv:x}','positions':pos[index],'uv':uv[index],'sha256':hashlib.sha256(raw).hexdigest()}

if __name__=='__main__':
    previous=read(Path(sys.argv[1]));current=read(ROOT/'assets/asian-female.glb')
    assert previous['uv'].shape==current['uv'].shape and np.array_equal(previous['uv'],current['uv']),'Triangle corner/UV order changed: do not enable compatibility'
    delta=np.linalg.norm(previous['positions']-current['positions'],axis=1)
    assert delta.max()<.01,'Large surface change requires separate migration review'
    report={'previous_model_key':previous['key'],'current_model_key':current['key'],'previous_glb_sha256':previous['sha256'],'current_glb_sha256':current['sha256'],'triangle_corners_compared':len(delta),'ordered_triangle_uvs_exactly_equal':True,'maximum_vertex_shift_m':float(delta.max()),'interpretation':'Same triangle and corner order; barycentric anchors follow the edited surface. Label offsets and sizes are preserved. Only this verified previous key is accepted.'}
    (ROOT/'assets/anchor-compatibility.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
