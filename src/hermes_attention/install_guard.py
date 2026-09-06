"""Pre-mutation ownership/path checks for the exact existing Jarvis runtime."""
from pathlib import Path
import os,stat,sqlite3,tempfile,hashlib,json,shutil

NAMES=('.hermes-ai-attention-project','src','config','specialists','scripts','.hermes','hermes')

def no_links(path,*,owner_from=None):
    path=Path(path).absolute()
    for candidate in [*reversed(path.parents),path]:
        if candidate.is_symlink():raise ValueError(f'Symbolic link in installation path: {candidate}')
        if candidate.exists() and owner_from and (candidate==owner_from or owner_from in candidate.parents):
            if candidate.stat().st_uid!=os.getuid():raise ValueError(f'Installation path is not owner-controlled: {candidate}')
    return path

def inspect_install(project_root,home):
    root=no_links(project_root);home=no_links(home)
    if not (root/'.hermes-ai-attention-project').is_file():raise ValueError('Marked project required')
    runtime=home/'.hermes/jarvis-runtime';base=home/'.hermes'
    for path in (base,runtime,base/'backups',base/'plugins',base/'desktop-plugins'):
        no_links(path,owner_from=base)
    if runtime.exists() and not (runtime/'.hermes-ai-attention-project').is_file():
        raise ValueError('Existing runtime lacks project ownership marker')
    source_db=root/'runtime-data/hermes_attention.sqlite3'
    if not (runtime/'runtime-data/hermes_attention.sqlite3').exists() and (source_db.exists() or source_db.is_symlink()):
        no_links(source_db,owner_from=root)
        if not source_db.is_file():raise ValueError('Source database must be regular')
    files=[]
    for name in NAMES:
        source=root/name
        if not source.exists():raise ValueError(f'Missing runtime source: {name}')
        no_links(runtime/name,owner_from=base)
        for path in ([source] if source.is_file() else [source,*source.rglob('*')]):
            no_links(path,owner_from=root)
            if not (path.is_file() or path.is_dir()):raise ValueError('Special installation input forbidden')
            if not path.is_file():continue
            if path.name=='.env' or 'runtime-data' in path.relative_to(root).parts:raise ValueError('Private data cannot be a runtime code install input')
            target=runtime/path.relative_to(root);no_links(target,owner_from=base)
            if '__pycache__' not in path.parts and path.suffix!='.pyc':files.append(str(path.relative_to(root)))
    for link,suffix in ((base/'plugins/hermes-attention','.hermes/plugins/hermes-attention'),(base/'desktop-plugins/hermes-attention','hermes/desktop-plugins/hermes-attention')):
        if link.is_symlink():
            if os.readlink(link) not in {str(root/suffix),str(runtime/suffix)}:raise ValueError('Unrelated plugin link must be preserved')
        elif link.exists():raise ValueError('Non-link plugin must be preserved')
    no_links(runtime/'runtime-data',owner_from=base)
    no_links(runtime/'runtime-data/hermes_attention.sqlite3',owner_from=base)
    web=companion_manifest(root)
    no_links(runtime/'companion-web',owner_from=base)
    return {'companion_assets':web,'runtime':str(runtime),'source_files':sorted(files),'credentials_untouched':True,'database_replace':False}


def first_database_backup(source,destination):
    """Exclusive first-install snapshot, including committed WAL pages."""
    source=Path(source).absolute();destination=Path(destination).absolute()
    no_links(source,owner_from=source.parent)
    no_links(destination,owner_from=destination.parent)
    if not source.is_file():raise ValueError('Regular source database required')
    if destination.exists():raise ValueError('Existing database must be preserved')
    fd,temporary=tempfile.mkstemp(prefix='.database-backup-',dir=destination.parent)
    os.close(fd)
    try:
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(temporary) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database backup integrity failed')
        os.link(temporary,destination)  # atomic no-overwrite, even if destination appears
    finally:
        os.unlink(temporary)


WEB_SUFFIXES={'.html','.js','.css','.svg','.png','.jpg','.jpeg','.gif','.webp','.ico','.woff','.woff2','.ttf','.json','.txt','.webmanifest','.wasm'}
def companion_manifest(root):
    root=Path(root);source=root/'jarvis/dist'
    if not source.exists():return None
    no_links(source,owner_from=root)
    if not (source/'index.html').is_file():raise ValueError('Compiled companion index missing')
    files={};total=0
    for path in source.rglob('*'):
        no_links(path,owner_from=root)
        relative=path.relative_to(source)
        if any(p.startswith('.') or p in {'node_modules','runtime-data'} for p in relative.parts):raise ValueError('Private/noncompiled companion input forbidden')
        if path.is_dir():continue
        if not path.is_file() or path.suffix.lower() not in WEB_SUFFIXES:raise ValueError('Unsupported companion asset')
        total+=path.stat().st_size
        if path.stat().st_size>50*1024**2 or total>100*1024**2:raise ValueError('Compiled companion assets exceed reviewed size bound')
        files[str(relative)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return {'files':dict(sorted(files.items())),'sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}

def install_companion_assets(root,home):
    root=Path(root);home=Path(home);checked=inspect_install(root,home);manifest=checked['companion_assets']
    if manifest is None:return {'installed':False,'reason':'compiled assets unavailable'}
    runtime=Path(checked['runtime']);target=runtime/'companion-web';source=root/'jarvis/dist'
    stage=Path(tempfile.mkdtemp(prefix='.companion-assets-',dir=runtime));stage.chmod(0o700)
    for relative,expected in manifest['files'].items():
        path=source/relative;no_links(path,owner_from=root)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Compiled asset changed during installation')
        output=stage/relative;output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,output)
        if hashlib.sha256(output.read_bytes()).hexdigest()!=expected:raise ValueError('Compiled asset copy mismatch')
    if companion_manifest(root)!=manifest:raise ValueError('Compiled asset inventory changed during installation')
    previous=None
    if target.exists():
        backup=home/'.hermes/backups';no_links(backup,owner_from=home/'.hermes');backup.mkdir(parents=True,exist_ok=True,mode=0o700)
        quarantine=Path(tempfile.mkdtemp(prefix='companion-web-before-',dir=backup));previous=quarantine/'companion-web'
        os.rename(target,previous)
    try:os.rename(stage,target)
    except Exception:
        if previous is not None:os.rename(previous,target)
        raise
    receipt={'installed':True,'assetSha256':manifest['sha256'],'files':manifest['files'],'previous':str(previous) if previous else None,'target':str(target)}
    record=runtime/'runtime-data/companion-assets-manifest.json';record.parent.mkdir(exist_ok=True,mode=0o700);no_links(record,owner_from=runtime)
    fd,tmp=tempfile.mkstemp(prefix='.companion-manifest-',dir=record.parent)
    with os.fdopen(fd,'w') as stream:json.dump(receipt,stream,indent=2)
    os.replace(tmp,record)
    return receipt
