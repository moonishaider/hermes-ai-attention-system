#!/usr/bin/env python3
"""Stable owned Hermes CUA command shim using official manifest/socket APIs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

def configuration(root=ROOT):
    from stat import S_ISREG
    marker=root/'.hermes-ai-attention-project'
    if not marker.is_file() or marker.is_symlink():raise PermissionError('Marked runtime required')
    path=root/'runtime-data/runtime-cua.json'
    for item in [path,*path.parents]:
        if item.is_symlink():raise PermissionError('Driver paths cannot be symbolic links')
    meta=path.stat()
    if not S_ISREG(meta.st_mode) or meta.st_uid!=os.getuid() or meta.st_mode&0o777!=0o600 or meta.st_size>16384:raise PermissionError('Private owner driver config required')
    value=json.loads(path.read_text())
    if set(value)!={'enabled','app','socket','stateDir','binarySha256'}:raise ValueError('Unknown driver config fields')
    expected={'app':root/'computer-use/cua-driver-0.23.2/CuaDriver.app','socket':root/'runtime-data/cua-driver.sock','stateDir':root/'runtime-data/cua-driver-state'}
    for key,path in expected.items():
        if value[key]!=str(path):raise PermissionError('Driver configuration path differs from reviewed runtime')
        for item in [path,*path.parents]:
            if item.is_symlink():raise PermissionError('Driver path redirected')
            if item.exists() and (item==root or root in item.parents) and item.stat().st_uid!=os.getuid():raise PermissionError('Driver path is not owner-controlled')
    binary=expected['app']/'Contents/MacOS/cua-driver'
    for item in [binary,*binary.parents]:
        if item.is_symlink():raise PermissionError('Driver executable path redirected')
    if not binary.is_file() or binary.is_symlink() or hashlib.sha256(binary.read_bytes()).hexdigest()!=value['binarySha256']:raise PermissionError('Pinned driver executable changed')
    return value,str(binary)

def invocation(args,value,binary):
    if not args or args[0] not in {'manifest','mcp','call','status','list-tools','describe','--help','--version'}:raise PermissionError('Unsupported maintained driver command')
    if any(a in {'--direct','--embedded','--dangerously-bypass-approvals','--no-permissions-gate','--grant','--permission-mode','--approve-capability-manifest','--socket'} or a.startswith(('--socket=','--grant=','--permission-mode=','--dangerously-','--embedded=')) for a in args):raise PermissionError('Driver authority and socket overrides are unavailable')
    if args[0] in {'mcp','call'} and value['enabled'] is not True:raise PermissionError('CuaDriver awaits owner permission readiness; runtime is disabled')
    return [binary,*args,*(['--socket',value['socket']] if args[0] in {'mcp','call','status'} else [])]

def main():
    value,binary=configuration();args=sys.argv[1:];command=invocation(args,value,binary)
    preserved={k:v for k,v in os.environ.items() if k in {'HOME','PATH','TMPDIR','LANG','LC_ALL','USER','LOGNAME'}}
    os.environ.clear();os.environ.update(preserved)
    os.environ['CUA_DRIVER_RS_TELEMETRY_ENABLED']='0';os.environ['CUA_DRIVER_RS_HOME']=value['stateDir']
    for key in ('CUA_DRIVER_PERMISSION_MODE','CUA_DRIVER_DANGEROUSLY_BYPASS_APPROVALS','CUA_DRIVER_EMBEDDED'):os.environ.pop(key,None)
    if args==['manifest']:
        manifest=json.loads(subprocess.check_output(command,text=True))
        manifest['mcp_invocation']={'command':str(Path(__file__).resolve()),'args':['mcp']}
        print(json.dumps(manifest))
    else:os.execv(binary,command)
if __name__=='__main__':
    try:main()
    except Exception as error:print(str(error),file=sys.stderr);raise SystemExit(2)
