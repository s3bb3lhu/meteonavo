"""Download exact Debian source packages corresponding to installed binaries."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from tools.collect_python_source import collect as collect_python


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def collect(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    # Use the same signed Debian suites as the runtime's binary packages.
    for file in Path('/etc/apt/sources.list.d').glob('*.sources'):
        content = file.read_text()
        content = re.sub(r'^Types: deb$', 'Types: deb deb-src', content, flags=re.M)
        file.write_text(content)
    run(['apt-get', 'update'])
    query = subprocess.check_output(['dpkg-query', '-W', '-f', '${db:Status-Status}\t${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n'], text=True)
    packages = []
    sources = {}
    for line in query.splitlines():
        state, binary, version, source, source_version = line.split('\t')
        if state != 'installed':
            continue
        source = source or binary.split(':')[0]
        source_version = source_version or version
        packages.append(dict(binary=binary, version=version, source=source, source_version=source_version))
        sources[(source, source_version)] = None
    for index, (source, version) in enumerate(sorted(sources), 1):
        print(f'Source {index}/{len(sources)}: {source} {version}', flush=True)
        # --download-only preserves upstream tarballs, Debian patches and .dsc.
        # An unavailable exact version fails publication; never silently substitute.
        run(['apt-get', 'source', '--download-only', '--only-source', '-y', f'{source}={version}'], cwd=destination)
    collect_python(destination)
    files = []
    for file in sorted(destination.iterdir()):
        if file.is_file():
            digest = hashlib.file_digest(file.open('rb'), 'sha256').hexdigest()
            files.append(dict(name=file.name, bytes=file.stat().st_size, sha256=digest))
    (destination/'debian-source-manifest.json').write_text(json.dumps(dict(packages=packages, files=files), indent=2)+'\n')
    for name, command in [('ffmpeg-build.txt', ['ffmpeg', '-version']), ('chromium-version.txt', ['chromium', '--version'])]:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        (destination/name).write_text(result.stdout+result.stderr)
    print(f'Exact corresponding sources collected: {len(sources)} source packages', flush=True)


if __name__ == '__main__':
    collect(sys.argv[1])
