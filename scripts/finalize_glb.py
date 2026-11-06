"""Finalize portable glTF material factors after Blender export.

Blender's MixRGB cloth tint is retained in the editable .blend file. The glTF
exporter does not bake that node, so write the equivalent baseColorFactor.
"""
import json
import struct
import sys
from pathlib import Path


def finalize(path_string: str) -> None:
    path = Path(path_string)
    raw = path.read_bytes()
    magic, version, _ = struct.unpack_from('<4sII', raw, 0)
    if magic != b'glTF' or version != 2:
        raise ValueError(f'Not a glTF 2.0 binary: {path}')
    chunks = []
    offset = 12
    document = None
    while offset < len(raw):
        length, kind = struct.unpack_from('<II', raw, offset)
        payload = raw[offset + 8:offset + 8 + length]
        if kind == 0x4E4F534A:
            document = json.loads(payload.decode('utf-8'))
        else:
            chunks.append((kind, payload))
        offset += 8 + length
    if document is None:
        raise ValueError(f'Missing JSON chunk: {path}')
    found = False
    for material in document.get('materials', []):
        if material.get('name') == 'Cloth_Cotton':
            material.setdefault('pbrMetallicRoughness', {})['baseColorFactor'] = [0.94, 0.975, 1.0, 1.0]
            found = True
    if not found:
        raise ValueError(f'Cloth_Cotton material not found: {path}')
    document.setdefault('asset', {}).setdefault('extras', {})['clothingPalette'] = 'cool-white-blue'
    payload = json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    payload += b' ' * ((-len(payload)) % 4)
    output = [(0x4E4F534A, payload), *chunks]
    total = 12 + sum(8 + len(chunk) for _, chunk in output)
    with path.open('wb') as handle:
        handle.write(struct.pack('<4sII', b'glTF', 2, total))
        for kind, chunk in output:
            handle.write(struct.pack('<II', len(chunk), kind))
            handle.write(chunk)
    print(f'FINALIZED {path} ({total} bytes)')


if __name__ == '__main__':
    for argument in sys.argv[1:]:
        finalize(argument)
