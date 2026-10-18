"""Preserve the original iris material multiplier in exported glTF 2.0.

Blender's exporter can omit this MixRGB factor. Explicit baseColorFactor is
portable and leaves geometry, UVs, embedded images and binary offsets intact.
"""
import json,struct
from pathlib import Path

def preserve_iris_factor(path):
    path=Path(path);data=path.read_bytes()
    magic,version,total=struct.unpack_from('<III',data)
    assert magic==0x46546c67 and version==2 and total==len(data)
    length,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    document=json.loads(data[20:20+length])
    iris=next(m for m in document['materials'] if m['name']=='Deep brown iris')
    iris['pbrMetallicRoughness']['baseColorFactor']=[.20,.40,.30,1]
    payload=json.dumps(document,separators=(',',':')).encode()
    payload+=b' '*((-len(payload))%4)
    rest=data[20+length:]
    result=struct.pack('<III',magic,version,20+len(payload)+len(rest))+struct.pack('<II',len(payload),kind)+payload+rest
    path.write_bytes(result)

if __name__=='__main__':
    import sys
    preserve_iris_factor(sys.argv[1])
