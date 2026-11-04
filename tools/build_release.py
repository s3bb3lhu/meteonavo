"""Build a source-only ZIP from an explicit allowlist, never from Docker volumes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT_FILES = {'Dockerfile', 'LICENSE', '.env.example', '.gitignore', '.dockerignore',
              'requirements.txt', 'requirements.lock', 'compose.yaml', 'compose.https.yaml',
              'RELEASE-AUDIT.json'}
SOURCE_DIRS = {'app', 'deploy', 'tests', 'tools', '.github'}
SKIP_DIRS = {'__pycache__', '.pytest_cache'}
INTERMEDIATE_FILES = {'app/static/maps/radar-geography.json',
                      'app/static/weather/photographic-atlas-v1.png'}
PRIVATE_DIRS = {'data', 'media', 'hls', 'work', 'backups', '.git', '.venv', 'service'}
PRIVATE_SUFFIXES = {'.key', '.pem', '.p12', '.pfx', '.sqlite', '.db', '.log', '.bak',
                    '.zip', '.tar', '.gz', '.tgz'}


def release_files(root):
    root = Path(root).resolve()
    candidates = [p for p in root.iterdir() if p.name in ROOT_FILES or p.suffix == '.md']
    for directory in sorted(SOURCE_DIRS):
        folder = root / directory
        if folder.is_symlink():
            raise ValueError('Source directory must not be a symlink: ' + directory)
        if folder.is_dir():
            candidates.extend(folder.rglob('*'))
    result = []
    for path in sorted(set(candidates)):
        relative = path.relative_to(root)
        if relative.as_posix() in INTERMEDIATE_FILES:
            continue
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError('Symlinks are not allowed in release sources: ' + str(relative))
        if not path.is_file():
            continue
        name = path.name.lower()
        # Existing compressed, public geography and hls.js assets are intentional.
        public_gzip = relative.as_posix() in {
            'app/static/maps/radar-geography.json.gz',
            'app/static/vendor/hls-1.7.4.light.min.js.gz',
        }
        private = any(part.lower() in PRIVATE_DIRS for part in relative.parts)
        private |= name.startswith('.env') and relative.as_posix() != '.env.example'
        private |= path.suffix.lower() in PRIVATE_SUFFIXES and not public_gzip
        private |= '.sqlite-' in name or '.db-' in name
        if private:
            raise ValueError('Private/runtime file in source allowlist: ' + str(relative))
        body = path.read_bytes()
        if re.search(rb'AIza[0-9A-Za-z_-]{35}', body):
            raise ValueError('Possible Google API key; value suppressed: ' + str(relative))
        result.append((relative.as_posix(), body))
    return result


def build(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError('Write release artifacts outside the source directory')
    files = release_files(root)
    manifest = dict(format=1, files=[dict(path=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
                                  for name, body in files])
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in files:
            archive.writestr('meteonavo/' + name, body)
        archive.writestr('meteonavo/RELEASE-MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + '.sha256').write_text(digest + '  ' + output.name + '\n')
    return dict(files=len(files), sha256=digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output)))
