
import json
import os
from pathlib import Path
import stat

def private_file(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent = path.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid(): raise PermissionError("Pasta privada inválida")
    path.parent.chmod(0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
    except FileExistsError: pass
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("Arquivo deve ser privado (0600), regular e do usuário")
    return path

def read_json(path: Path, max_bytes=2_000_000):
    p = Path(path)
    info = p.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes: raise ValueError("Arquivo JSON inválido ou muito grande")
    return json.loads(p.read_text(encoding='utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Número JSON inválido")))

def write_private_json(path: Path, data):
    path = private_file(path)
    fd = os.open(path, os.O_WRONLY | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
