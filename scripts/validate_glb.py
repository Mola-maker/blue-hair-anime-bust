"""Validate the delivered GLB structure without third-party dependencies."""
import json
import struct
import sys
from pathlib import Path


def inspect(path_string):
    path = Path(path_string)
    with path.open('rb') as handle:
        magic, version, total = struct.unpack('<4sII', handle.read(12))
        if magic != b'glTF' or version != 2 or total != path.stat().st_size:
            raise ValueError(f'Invalid glTF header: {path}')
        length, kind = struct.unpack('<II', handle.read(8))
        if kind != 0x4E4F534A:
            raise ValueError(f'Missing JSON chunk: {path}')
        document = json.loads(handle.read(length))
    primitives = [primitive for mesh in document.get('meshes', []) for primitive in mesh['primitives']]
    triangles = sum(document['accessors'][primitive['indices']]['count'] // 3 for primitive in primitives)
    cloth = next(material for material in document['materials'] if material.get('name') == 'Cloth_Cotton')
    result = {
        'file': path.name,
        'bytes': path.stat().st_size,
        'triangles': triangles,
        'primitives': len(primitives),
        'joints': len(document['skins'][0]['joints']),
        'animations': len(document.get('animations', [])),
        'animation_channels': sum(len(animation['channels']) for animation in document.get('animations', [])),
        'all_primitives_skinned': all('JOINTS_0' in primitive['attributes'] and 'WEIGHTS_0' in primitive['attributes'] for primitive in primitives),
        'cloth_baseColorFactor': cloth['pbrMetallicRoughness'].get('baseColorFactor'),
    }
    assert result['joints'] == 18
    assert result['animations'] == 1
    assert result['animation_channels'] == 54
    assert result['all_primitives_skinned']
    assert result['cloth_baseColorFactor'] == [0.94, 0.975, 1.0, 1.0]
    return result


if __name__ == '__main__':
    print(json.dumps([inspect(argument) for argument in sys.argv[1:]], ensure_ascii=False, indent=2))
