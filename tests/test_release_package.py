import importlib.util
from pathlib import Path
import zipfile
import pytest

spec = importlib.util.spec_from_file_location('build_release', Path(__file__).parents[1] / 'tools/build_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_source_package_excludes_operator_data_and_contains_manifest(tmp_path):
    root = tmp_path / 'source'
    (root / 'app').mkdir(parents=True)
    (root / 'app/main.py').write_text('print("source only")')
    (root / '.env.example').write_text('PORT=7373\n')
    (root / '.env').write_text('PRIVATE_RUNTIME_VALUE=private\n')
    (root / 'data').mkdir()
    (root / 'data/studio.sqlite').write_bytes(b'private database')
    (root / 'backups').mkdir()
    (root / 'backups/secret.pem').write_text('private certificate')
    (root / 'app/static/weather').mkdir(parents=True)
    (root / 'app/static/weather/photographic-atlas-v1.png').write_bytes(b'unused intermediate')
    (root / 'app/static/maps').mkdir(parents=True)
    (root / 'app/static/maps/radar-geography.json').write_text('{}')
    output = tmp_path / 'release.zip'
    result = release.build(root, output)
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {'meteonavo/app/main.py', 'meteonavo/.env.example', 'meteonavo/RELEASE-MANIFEST.json'}
        assert b'private' not in b''.join(archive.read(name) for name in archive.namelist())
    assert result['files'] == 2 and output.with_suffix('.zip.sha256').is_file()


def test_private_files_inside_source_tree_abort_without_echoing_values(tmp_path):
    root = tmp_path / 'source'
    (root / 'app').mkdir(parents=True)
    for name in ['operator.key', 'studio.sqlite-wal', '.env.local', 'backup.pfx']:
        path = root / 'app' / name
        path.write_text('private-value-must-not-be-printed')
        with pytest.raises(ValueError) as error:
            release.build(root, tmp_path / 'release.zip')
        assert 'private-value-must-not-be-printed' not in str(error.value)
        path.unlink()
    (root / 'app/key.js').write_text('const key="' + 'AIza' + 'x' * 35 + '"')
    with pytest.raises(ValueError, match='Possible Google API key'):
        release.build(root, tmp_path / 'release.zip')
