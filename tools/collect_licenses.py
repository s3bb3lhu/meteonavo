"""Export installed Python distribution metadata and existing license notices."""
import importlib.metadata
import json
import re
import shutil
import sys
from pathlib import Path


def collect(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    for distribution in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
        name = distribution.metadata['Name']
        folder = destination / re.sub(r'[^a-zA-Z0-9_.-]', '_', name + '-' + distribution.version)
        folder.mkdir(exist_ok=True)
        copied = []
        for entry in distribution.files or []:
            if not re.search(r'(^|/)(license[^/]*|copying[^/]*|notice[^/]*|copyright[^/]*)$', str(entry), re.I):
                continue
            source = Path(distribution.locate_file(entry))
            if not source.is_file():
                continue
            target = folder / (str(len(copied) + 1) + '-' + source.name)
            shutil.copyfile(source, target)
            copied.append({'original': str(entry), 'copy': str(target.relative_to(destination))})
        inventory.append({'name': name, 'version': distribution.version,
                          'license_expression': distribution.metadata.get('License-Expression'),
                          'license': distribution.metadata.get('License'),
                          'project_urls': distribution.metadata.get_all('Project-URL', []),
                          'notices': copied})
    (destination / 'python-inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    return inventory


if __name__ == '__main__':
    collect(sys.argv[1] if len(sys.argv) > 1 else 'third-party-licenses')
