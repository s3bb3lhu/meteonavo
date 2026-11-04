"""Include the exact CPython upstream sources and public build configuration."""
import hashlib,json,os,sys,sysconfig,urllib.request
from pathlib import Path


def collect(destination):
    folder=Path(destination);folder.mkdir(parents=True,exist_ok=True)
    version=sys.version.split()[0]
    assert all(c.isdigit() or c=='.' for c in version)
    name=f'Python-{version}.tar.xz'
    url=f'https://www.python.org/ftp/python/{version}/{name}'
    target=folder/name
    with urllib.request.urlopen(url,timeout=120) as response,target.open('wb') as output:
        while block:=response.read(1024*1024):output.write(block)
    actual=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
    expected=os.getenv('PYTHON_SHA256','')
    if expected:assert actual==expected,'CPython source checksum mismatch'
    (folder/'cpython-source.json').write_text(json.dumps(dict(version=version,url=url,sha256=actual,
        upstream_image_checksum_verified=bool(expected),build={key:sysconfig.get_config_var(key) for key in ['CONFIG_ARGS','CFLAGS','LDFLAGS','CC','MULTIARCH']}),indent=2)+'\n')
    print('Exact CPython source included',flush=True)


if __name__=='__main__':collect(sys.argv[1])
