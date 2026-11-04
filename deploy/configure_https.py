"""Validate an existing certificate and configure the HTTPS Compose overlay.

Run as the host administrator, from the project root. Never prints .env contents.
"""
import argparse
import ipaddress
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def configure(host, cert_name, cert_dir, project, backup_dir):
    try:address=ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?',host):raise ValueError('Invalid public host')
        check='-checkhost'
    else:
        if address.version!=4:raise ValueError('Use an IPv4 address or DNS hostname')
        check='-checkip'
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,200}',cert_name):raise ValueError('Invalid certificate name')
    cert_dir=Path(cert_dir).resolve()
    if any(c in str(cert_dir) for c in '\n\r\x00:#\"\x27$'):raise ValueError('Invalid certificate directory')
    lineage=cert_dir/'live'/cert_name
    for file in ['fullchain.pem','privkey.pem']:
        if not (lineage/file).is_file():raise ValueError('Missing certificate file: '+file)
    for arguments in [['-checkend','86400'],[check,host]]:
        result=subprocess.run(['openssl','x509','-in',str(lineage/'fullchain.pem'),'-noout',*arguments],capture_output=True,timeout=15)
        if result.returncode:raise ValueError('Certificate expires soon or does not cover the public host')
    verified=subprocess.run(['openssl','verify','-untrusted',str(lineage/'fullchain.pem'),str(lineage/'fullchain.pem')],capture_output=True,timeout=15)
    public=subprocess.run(['openssl','x509','-in',str(lineage/'fullchain.pem'),'-pubkey','-noout'],capture_output=True,timeout=15)
    private=subprocess.run(['openssl','pkey','-in',str(lineage/'privkey.pem'),'-pubout','-passin','pass:'],capture_output=True,timeout=15)
    if verified.returncode or public.returncode or private.returncode or public.stdout.strip()!=private.stdout.strip():raise ValueError('Untrusted certificate chain or mismatching private key')
    project=Path(project).resolve();env=project/'.env'
    if env.is_symlink():raise ValueError('Use a regular .env file, not a symbolic link')
    if not (project/'compose.https.yaml').is_file():raise ValueError('Run from the project directory')
    text=env.read_text(encoding='utf-8') if env.exists() else (project/'.env.example').read_text(encoding='utf-8')
    port_match=re.search(r'^PORT=[\"\x27]?(\d+)[\"\x27]?\s*(?:#.*)?$',text,re.M);port=int(port_match[1]) if port_match else 7373
    if re.search(r'^PORT=',text,re.M) and not port_match:raise ValueError('Invalid public port')
    if not 1<=port<=65535:raise ValueError('Invalid public port')
    previous=re.search(r'^COMPOSE_FILE=(.*)$',text,re.M)
    if previous and previous[1].strip() not in ('','compose.yaml','compose.yaml:compose.https.yaml'):raise ValueError('Custom COMPOSE_FILE found; merge the HTTPS overlay manually')
    values={'PUBLIC_HOST':host,'TLS_CERT_NAME':cert_name,'TLS_CERT_DIR':str(cert_dir),
            'PUBLIC_BASE_URL':f'https://{host}:{port}','COMPOSE_FILE':'compose.yaml:compose.https.yaml'}
    backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    if env.exists():
        backup=backup_dir/('env-before-https-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        shutil.copyfile(env,backup);backup.chmod(0o600)
    for key,value in values.items():
        pattern=r'^'+re.escape(key)+r'=.*$'
        text=re.sub(pattern,lambda _:key+'='+value,text,flags=re.M) if re.search(pattern,text,re.M) else text.rstrip()+'\n'+key+'='+value+'\n'
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=project,prefix='.env.https-',delete=False) as file:
        file.write(text);temporary=Path(file.name)
    temporary.replace(env);env.chmod(0o600)
    print(f'Configured HTTPS administration: https://{host}:{port}')
    print(f'HTTP IPTV remains available: http://{host}:{port}')
    print('Next: docker compose -p weather-studio config --quiet; docker compose -p weather-studio up -d --build')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host');parser.add_argument('cert_name')
    parser.add_argument('--cert-dir',default='/etc/letsencrypt')
    parser.add_argument('--project',default='.')
    parser.add_argument('--backup-dir',default='/var/backups/meteonavo-https')
    args=parser.parse_args()
    configure(args.host,args.cert_name,args.cert_dir,args.project,args.backup_dir)
