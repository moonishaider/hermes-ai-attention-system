#!/usr/bin/env python3
"""Exact-manifest cleanup of reproducible Cargo intermediates; dry-run by default.

Apply only after separately verifying installed app and required recovery sets.
Never counts same-filesystem staging as reclaimed storage.
"""
from pathlib import Path
import argparse,hashlib,json,os,stat,subprocess,tempfile

SUBROOTS=('jarvis/src-tauri/target/release/deps','jarvis/src-tauri/target/debug/incremental')

def active_build():
    result=subprocess.run(['ps','-axo','comm='],capture_output=True,text=True,check=True)
    return any(Path(line.strip()).name in {'cargo','rustc','rustdoc','clang','clang++','ld','ld64'} for line in result.stdout.splitlines())

def safe_path(root,relative):
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:raise ValueError('invalid relative candidate')
    allowed=next((base for base in SUBROOTS if str(rel).startswith(base+'/')),None)
    if not allowed:raise ValueError('outside generated intermediate roots')
    if rel.suffix=='.lock' or (allowed==SUBROOTS[0] and rel.suffix not in {'.rlib','.rmeta','.d','.o'}):raise ValueError('protected or unsupported intermediate')
    current=root
    for part in rel.parts:
        current=current/part
        info=current.lstat()
        if stat.S_ISLNK(info.st_mode):raise ValueError('symlink forbidden')
        if info.st_uid!=os.getuid() or info.st_mode&0o022:raise ValueError('candidate path ownership or write permissions unsafe')
    return current

def identity(path,*,dir_fd=None):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dir_fd)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:raise ValueError('only singly linked regular files allowed')
        digest=hashlib.sha256()
        while chunk:=os.read(fd,1024*1024):digest.update(chunk)
        after=os.fstat(fd)
        if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('candidate changed during read')
        return {'device':after.st_dev,'inode':after.st_ino,'size':after.st_size,'nlink':after.st_nlink,'mtimeNs':after.st_mtime_ns,'ctimeNs':after.st_ctime_ns,'sha256':digest.hexdigest(),'allocatedBytes':after.st_blocks*512}
    finally:os.close(fd)

def verify(path,entry,*,moved=False,dir_fd=None):
    actual=identity(path,dir_fd=dir_fd)
    fields=('device','inode','size','nlink','mtimeNs','sha256') if moved else ('device','inode','size','nlink','mtimeNs','ctimeNs','sha256')
    if any(actual[key]!=entry.get(key) for key in fields):raise ValueError('candidate identity differs from reviewed manifest')
    return actual

def execute(root,manifest_bytes,expected_digest,*,apply=False,build_probe=active_build):
    root=Path(root).absolute()
    if root.is_symlink() or root.resolve()!=root or not (root/'.hermes-ai-attention-project').is_file():raise ValueError('marked non-symlink project required')
    if hashlib.sha256(manifest_bytes).hexdigest()!=expected_digest:raise ValueError('manifest digest mismatch')
    manifest=json.loads(manifest_bytes)
    if manifest.get('root')!=str(root):raise ValueError('manifest belongs to another project')
    entries=manifest.get('files')
    if not isinstance(entries,list) or not entries or len(entries)>20000:raise ValueError('bounded exact file manifest required')
    names=[e['path'] for e in entries]
    if len(names)!=len(set(names)):raise ValueError('duplicate candidate')
    if build_probe():raise ValueError('active compiler/build; retry after it stops')
    checked=[(safe_path(root,e['path']),e) for e in entries]
    for path,entry in checked:verify(path,entry)
    before=os.statvfs(root);free_before=before.f_bavail*before.f_frsize
    result={'mode':'apply' if apply else 'dry-run','files':len(entries),'logicalBytes':sum(e['size'] for e in entries),'allocatedBytesEstimate':sum(e.get('allocatedBytes',0) for e in entries),'deletedFiles':0,'deletedLogicalBytes':0,'deletedAllocatedBytesEstimate':0,'freeSpaceDelta':0}
    if not apply:return result
    staging_parent=root/'jarvis/src-tauri/target'
    # All candidate ancestors, including staging parent, passed no-symlink/owner checks.
    stage=Path(tempfile.mkdtemp(prefix='.reviewed-cleanup-',dir=staging_parent))
    result['journal']=str(stage/'journal.jsonl')
    stage_fd=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    if os.fstat(stage_fd).st_ino!=stage.lstat().st_ino:
        os.close(stage_fd);raise ValueError('staging directory changed')
    def record(value):
        fd=os.open('journal.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=stage_fd)
        with os.fdopen(fd,'a') as out:out.write(json.dumps(value)+'\n');out.flush();os.fsync(out.fileno())
        os.fsync(stage_fd)
    try:
        for index,(path,entry) in enumerate(checked):
            if build_probe():raise ValueError('build started; remaining files preserved')
            path=safe_path(root,entry['path']);verify(path,entry)
            moved=str(index)
            record({'state':'before-move','original':entry['path'],'staged':moved,'expected':entry})
            os.rename(path,moved,dst_dir_fd=stage_fd)
            # Rename can change ctime. Open/unlink relative to the held stage inode.
            # This is not OS isolation against a hostile process with the same UID.
            verify(moved,entry,moved=True,dir_fd=stage_fd)
            record({'state':'validated','staged':moved})
            if build_probe():raise ValueError('build started; validated staged file retained, not deleted')
            verify(moved,entry,moved=True,dir_fd=stage_fd);os.unlink(moved,dir_fd=stage_fd)
            record({'state':'deleted','original':entry['path'],'staged':moved})
            result['deletedFiles']+=1;result['deletedLogicalBytes']+=entry['size'];result['deletedAllocatedBytesEstimate']+=entry.get('allocatedBytes',0)
    except Exception as error:
        raise ValueError(f'{error}; exact recovery journal: {stage}/journal.jsonl') from error
    finally:os.close(stage_fd)
    after=os.statvfs(root);result['freeSpaceDelta']=after.f_bavail*after.f_frsize-free_before
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('manifest');parser.add_argument('digest');parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try:print(json.dumps(execute(args.root,Path(args.manifest).read_bytes(),args.digest,apply=args.apply),indent=2));return 0
    except Exception as error:print(json.dumps({'ok':False,'error':str(error),'recovery':'Inspect any private target/.reviewed-cleanup-* journal; never delete unvalidated staged files.'}));return 2
if __name__=='__main__':raise SystemExit(main())
