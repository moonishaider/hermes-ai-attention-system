#!/usr/bin/env python3
"""Reviewable exact-path candidate activation. Default is read-only; never upgrades vendor venv.

Requires the owner runtime/app to be stopped beforehand. Failed activation retains
private backups; rollback never replaces live databases or credentials.
"""
from pathlib import Path
import argparse,hashlib,json,os,plistlib,shutil,stat,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'src'))
from hermes_attention.install_guard import inspect_install,no_links,NAMES,companion_manifest
RUNTIME_NAMES=(*NAMES,'companion-web')
BUNDLE='com.moonishaider.jarvis'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def tree(path):
    path=Path(path);no_links(path)
    values=[]
    for item in sorted([path,*path.rglob('*')]):
        if '__pycache__' in item.relative_to(path).parts or item.suffix=='.pyc':continue
        if item.is_symlink():raise ValueError('Bundle/code symlinks require separate review')
        if item.stat().st_uid!=os.getuid():raise ValueError('Activation input is not owned by this user')
        if item.is_file():values.append((str(item.relative_to(path)),sha(item)))
        elif not item.is_dir():raise ValueError('Special activation input refused')
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()
def signature(app,bundle=BUNDLE):
    with (app/'Contents/Info.plist').open('rb') as stream:info=plistlib.load(stream)
    if info.get('CFBundleIdentifier')!=bundle:raise ValueError('Unrelated application identifier')
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True,capture_output=True)
    result=subprocess.run(['/usr/bin/codesign','--display','-r-',str(app)],check=True,capture_output=True,text=True)
    return (result.stdout+result.stderr).strip()
def paths(root=ROOT,home=None):
    home=Path(home or Path.home());candidate=root/'runtime-data/goal-09/python312-candidate'
    lock=sha(candidate/'freeze.txt')[:16]
    return {'root':root,'home':home,'candidate':candidate,'app':Path('/Applications/Jarvis.app'),
            'built':root/'jarvis/src-tauri/target/release/bundle/macos/Jarvis.app',
            'runtime':home/'.hermes/jarvis-runtime','backup_root':home/'.hermes/backups',
            'final_env':home/'.hermes/jarvis-runtime/python-envs'/('py312-'+lock),
            'driver_source':root/'runtime-data/goal-09/cua-driver-0.23.2/CuaDriver.app',
            'driver_target':home/'.hermes/jarvis-runtime/computer-use/cua-driver-0.23.2/CuaDriver.app',
            'bundled':home/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'}
def soul_file(path,owner_root):
    no_links(path,owner_from=owner_root)
    meta=path.stat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_uid!=os.getuid():raise PermissionError('SOUL must be an owned regular nonlinked file')
    return sha(path)

def soul_plan(p):
    active=p['home']/'.hermes/SOUL.md';desired=p['root']/'hermes/SOUL.md'
    current=soul_file(active,p['home']);previous=soul_file(p['runtime']/'hermes/SOUL.md',p['runtime'])
    if current!=previous:raise PermissionError('Active SOUL differs from the previous runtime policy; preserve and review it')
    return {'active':str(active),'oldSha':current,'newSha':soul_file(desired,p['root'])}

def replace_soul(source,destination,expected,owner_root):
    # One exact owned policy file; no config or USER/memory paths enter here.
    if soul_file(destination,owner_root)!=expected:raise PermissionError('Active SOUL changed; refusing policy overwrite')
    no_links(source)
    data=source.read_bytes();fd,tmp=tempfile.mkstemp(prefix='.jarvis-soul-',dir=destination.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        if soul_file(destination,owner_root)!=expected:raise PermissionError('Active SOUL changed during policy staging')
        os.replace(tmp,destination)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def restore_soul(p,backup,plan,*,allow_unapplied=False):
    policy=plan['soul'];active=p['home']/'.hermes/SOUL.md';saved=backup/'SOUL.md'
    if policy['active']!=str(active) or soul_file(saved,p['home'])!=policy['oldSha']:raise PermissionError('SOUL rollback receipt or backup differs')
    current=soul_file(active,p['home'])
    if allow_unapplied and current==policy['oldSha']:return
    if current!=policy['newSha']:raise PermissionError('Active SOUL changed after candidate installation; rollback will not overwrite it')
    replace_soul(saved,active,policy['newSha'],p['home'])

def build_plan(p):
    inspect_install(p['root'],p['home'])
    for key in ('candidate','app','built','runtime','final_env','backup_root'):no_links(p[key],owner_from=p[key] if key in {'app','built'} else p['home'])
    if not p['app'].is_dir() or not p['built'].is_dir():raise ValueError('Existing app and newly built app are required')
    for filename in ('proof.json','freeze.txt'):
        item=p['candidate']/filename;no_links(item,owner_from=p['home'])
        if not item.is_file():raise ValueError('Regular candidate evidence required')
    proof=json.loads((p['candidate']/'proof.json').read_text())
    if (proof.get('python'),proof.get('sqlite'),proof.get('gateway_health_status'))!=('3.12.14','3.53.1',200):raise ValueError('Candidate compatibility proof missing')
    source=p['home']/'.hermes/hermes-agent/tools/mcp_tool.py'
    if sha(source)!=proof.get('zoom_patch_sha256'):raise ValueError('Reviewed Zoom source changed; revalidate candidate')
    web=companion_manifest(p['root'])
    if web is None:raise ValueError('Build compiled frontend before activation')
    code={name:tree(p['root']/name) if (p['root']/name).is_dir() else sha(p['root']/name) for name in NAMES}
    return {'schema':1,'soul':soul_plan(p),'app':str(p['app']),'built':str(p['built']),'runtime':str(p['runtime']),
            'finalPython':str(p['final_env']/'bin/python'),'sourceCode':code,'oldAppSha':tree(p['app']),
            'newAppSha':tree(p['built']),'oldSignature':signature(p['app']),'newSignature':signature(p['built']),
            'driverAppSha':tree(p['driver_source']),'driverSignature':signature(p['driver_source'],'com.trycua.driver'),
            'companionAssets':web,'dependencySha':sha(p['candidate']/'freeze.txt'),'proofSha':sha(p['candidate']/'proof.json'),
            'permissionContinuity':'Not guaranteed: ad-hoc designated requirements can bind the old cdhash. Recheck existing macOS permissions after replacement; this helper never changes TCC.',
            'databaseReplacement':False,'credentialChanges':False,'vendorVenvChanges':False}
def digest(plan):return hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
def private_json(path,value):
    no_links(path,owner_from=path.parent)
    fd,tmp=tempfile.mkstemp(prefix='.activation-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def require_stopped(p):
    output=subprocess.check_output(['/bin/ps','-axo','pid=,command='],text=True)
    for line in output.splitlines():
        if str(os.getpid())==line.strip().split(' ',1)[0]:continue
        if str(p['app']/'Contents/MacOS/') in line or ('hermes' in line and 'gateway run' in line):raise ValueError('Stop the owned Jarvis app and Hermes gateway before activation')
def code_digest(runtime):
    return {name:tree(runtime/name) if (runtime/name).is_dir() else sha(runtime/name) for name in RUNTIME_NAMES if (runtime/name).exists()}

def code_backup(runtime,backup):
    target=backup/'runtime-code';target.mkdir(mode=0o700)
    for name in RUNTIME_NAMES:
        source=runtime/name
        if source.is_dir():shutil.copytree(source,target/name,symlinks=True)
        elif source.is_file():shutil.copy2(source,target/name)

def restore_code(runtime,backup):
    # Preserve every replaced/new file in an exact owned quarantine. No deletion
    # and no database/credential paths enter the named-code restore operation.
    quarantine=Path(tempfile.mkdtemp(prefix='failed-runtime-code-',dir=backup))
    quarantine.chmod(0o700);moved=[]
    for name in RUNTIME_NAMES:
        source=backup/'runtime-code'/name;destination=runtime/name
        no_links(destination,owner_from=runtime)
        if destination.exists():
            os.rename(destination,quarantine/name);moved.append(name)
        if source.is_dir():shutil.copytree(source,destination,symlinks=True)
        elif source.is_file():shutil.copy2(source,destination)
    private_json(quarantine/'restore-manifest.json',{'preservedNames':moved,'restoredRuntime':str(runtime)})
    return quarantine

def private_record(path,owner_root):
    path=Path(path)
    if '..' in path.parts:raise PermissionError('Private receipt traversal refused')
    no_links(path,owner_from=owner_root)
    meta=path.stat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_uid!=os.getuid() or meta.st_mode&0o777!=0o600 or meta.st_size>1024*1024:raise PermissionError('Private owner activation record required')
    return json.loads(path.read_text())

def freeze_lines(text):
    return sorted(line.strip() for line in text.splitlines() if line.strip())

def verify_reusable_environment(p,plan):
    """Validate an already activated exact environment without installing anything."""
    python=p['final_env']/'bin/python';no_links(python,owner_from=p['runtime'])
    if not python.is_file() or not os.access(python,os.X_OK):raise PermissionError('Existing interpreter is not an owned executable')
    config=private_record(p['runtime']/'runtime-data/runtime-python.json',p['runtime'])
    if config.get('python')!=str(python):raise PermissionError('Existing environment is not the selected runtime interpreter')
    receipt=Path(config.get('candidateReceipt',''))
    if receipt.name!='activation-plan.json' or receipt.parent.parent!=p['backup_root'] or not receipt.parent.name.startswith('jarvis-candidate-before-'):raise PermissionError('Existing interpreter lacks an exact owned activation receipt')
    prior=private_record(receipt,p['home'])
    if prior.get('finalPython')!=str(python) or prior.get('dependencySha')!=plan['dependencySha'] or prior.get('runtime')!=str(p['runtime']):raise PermissionError('Existing environment receipt does not match this reviewed dependency snapshot')
    outcome=private_record(receipt.parent/'activation-result.json',p['home'])
    if outcome.get('status')!='installed-not-launched' or outcome.get('python')!=str(python):raise PermissionError('Environment has no successful prior activation receipt')
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    actual=subprocess.check_output([str(python),'-m','pip','--isolated','freeze'],text=True,env=env,timeout=60)
    if freeze_lines(actual)!=freeze_lines((p['candidate']/'freeze.txt').read_text()):raise PermissionError('Existing environment packages differ from the reviewed snapshot; no repair or upgrade was attempted')
    subprocess.run([str(python),'-m','pip','--isolated','check'],check=True,env=env,timeout=60)
    subprocess.run([str(python),'-c',"import sys,sqlite3,pypdf,docx,openpyxl,reportlab,PIL,pypdfium2,openai; assert sys.version_info[:3]==(3,12,14); assert sqlite3.sqlite_version=='3.53.1'"],check=True,env=env,timeout=60)
    return python

def activate(p,reviewed):
    plan=build_plan(p)
    if digest(plan)!=reviewed:raise PermissionError('Fresh reviewed plan digest required')
    require_stopped(p)
    if shutil.disk_usage(p['home']).free<2*1024**3:raise ValueError('At least 2 GiB free disk required')
    if p['final_env'].exists():
        python=verify_reusable_environment(p,plan)
    else:
        # Build directly at permanent path: venv shebangs are not relocatable.
        p['final_env'].parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        subprocess.run([str(p['bundled']),'-m','venv','--copies',str(p['final_env'])],check=True)
        python=p['final_env']/'bin/python';no_links(python,owner_from=p['runtime'])
        subprocess.run([str(python),'-m','pip','--isolated','install','--no-cache-dir','--only-binary=:all:','--index-url','https://pypi.org/simple','-r',str(p['candidate']/'freeze.txt')],check=True)
        subprocess.run([str(python),'-m','pip','check'],check=True)
        subprocess.run([str(python),'-c',"import sqlite3,pypdf,docx,openpyxl,reportlab,PIL,pypdfium2,openai; assert sqlite3.sqlite_version=='3.53.1'"],check=True)
    no_links(p['driver_target'],owner_from=p['runtime'])
    if p['driver_target'].exists():
        if tree(p['driver_target'])!=plan['driverAppSha']:raise PermissionError('Existing pinned driver differs; preserve and review it')
    else:
        p['driver_target'].parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        shutil.copytree(p['driver_source'],p['driver_target']);signature(p['driver_target'],'com.trycua.driver')
    # Re-check all reviewed source/app inputs after dependency preparation.
    if digest(build_plan(p))!=reviewed:raise PermissionError('Activation inputs changed while preparing dependencies')
    require_stopped(p)
    p['backup_root'].mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=Path(tempfile.mkdtemp(prefix='jarvis-candidate-before-',dir=p['backup_root']));backup.chmod(0o700)
    shutil.copytree(p['app'],backup/'Jarvis.app')
    code_backup(p['runtime'],backup)
    config=p['runtime']/'runtime-data/runtime-python.json'
    if config.exists():
        no_links(config,owner_from=p['runtime'])
        if config.stat().st_mode&0o077:raise ValueError('Runtime Python config is not private')
        shutil.copy2(config,backup/'runtime-python.json')
    cua_config=p['runtime']/'runtime-data/runtime-cua.json';cua_enabled=True
    if cua_config.exists():
        cua_enabled=private_record(cua_config,p['runtime']).get('enabled') is True
        no_links(cua_config,owner_from=p['runtime'])
        if cua_config.stat().st_mode&0o077:raise ValueError('Driver config is not private')
        shutil.copy2(cua_config,backup/'runtime-cua.json')
    active_soul=p['home']/'.hermes/SOUL.md'
    if soul_file(active_soul,p['home'])!=plan['soul']['oldSha']:raise PermissionError('Active SOUL changed before backup')
    shutil.copy2(active_soul,backup/'SOUL.md')
    private_json(backup/'activation-plan.json',plan)
    # The reviewed runtime installer makes its own exclusive code-only backup.
    try:subprocess.run(['/bin/bash',str(p['root']/'scripts/install_jarvis_runtime.sh')],check=True)
    except Exception:
        restore_code(p['runtime'],backup)
        raise
    try:stage=Path(tempfile.mkdtemp(prefix='.Jarvis-candidate-',dir=p['app'].parent))
    except Exception:
        restore_code(p['runtime'],backup)
        raise
    previous=stage/'previous.app';replacement=stage/'replacement.app'
    try:
        private_json(backup/'activation-stage.json',{'stage':str(stage),'previous':str(previous),'replacement':str(replacement),'destination':str(p['app'])})
        shutil.copytree(p['built'],replacement);signature(replacement)
        if tree(replacement)!=plan['newAppSha']:raise ValueError('Staged app changed')
        os.rename(p['app'],previous)
        os.rename(replacement,p['app']);signature(p['app'])
        private_json(config,{'python':str(python),'candidateReceipt':str(backup/'activation-plan.json')})
        private_json(cua_config,{'enabled':cua_enabled,'app':str(p['driver_target']),'socket':str(p['runtime']/'runtime-data/cua-driver.sock'),'stateDir':str(p['runtime']/'runtime-data/cua-driver-state'),'binarySha256':sha(p['driver_target']/'Contents/MacOS/cua-driver')})
        desired_soul=p['root']/'hermes/SOUL.md'
        if soul_file(desired_soul,p['root'])!=plan['soul']['newSha']:raise PermissionError('Reviewed SOUL source changed')
        replace_soul(desired_soul,active_soul,plan['soul']['oldSha'],p['home'])
        private_json(backup/'activation-result.json',{'status':'installed-not-launched','python':str(python),'appBackup':str(backup/'Jarvis.app'),'retainedPrevious':str(previous),'runtimeCodeSha':code_digest(p['runtime']),'permissions':'require read-only recheck'})
        return {'status':'installed-not-launched','backup':str(backup),'python':str(python)}
    except Exception:
        if previous.exists():
            if p['app'].exists():os.rename(p['app'],stage/'failed.app')
            os.rename(previous,p['app'])
        if (backup/'runtime-python.json').exists():shutil.copy2(backup/'runtime-python.json',config)
        elif config.exists():config.unlink()
        if (backup/'runtime-cua.json').exists():shutil.copy2(backup/'runtime-cua.json',cua_config)
        elif cua_config.exists():cua_config.unlink()
        restore_code(p['runtime'],backup)
        restore_soul(p,backup,plan,allow_unapplied=True)
        private_json(backup/'activation-result.json',{'status':'failed-needs-review','retainedStage':str(stage),'appPath':str(p['app']),'codeRollback':'Restore only installer code snapshot; never replace runtime-data or credentials'})
        raise

def rollback(p,backup):
    backup=Path(backup).absolute()
    if backup.parent!=p['backup_root'] or not backup.name.startswith('jarvis-candidate-before-'):raise PermissionError('Exact owned activation backup required')
    no_links(backup,owner_from=p['home']);require_stopped(p)
    plan=json.loads((backup/'activation-plan.json').read_text());receipt=json.loads((backup/'activation-result.json').read_text())
    if plan['app']!=str(p['app']) or plan['runtime']!=str(p['runtime']) or receipt['status']!='installed-not-launched':raise PermissionError('Backup does not describe this active candidate')
    if tree(p['app'])!=plan['newAppSha'] or code_digest(p['runtime'])!=receipt['runtimeCodeSha']:raise PermissionError('App/runtime changed since activation; do not overwrite newer work')
    original=backup/'Jarvis.app';signature(original)
    if tree(original)!=plan['oldAppSha']:raise PermissionError('Original app backup changed')
    if 'soul' in plan:
        if soul_file(p['home']/'.hermes/SOUL.md',p['home'])!=plan['soul']['newSha'] or soul_file(backup/'SOUL.md',p['home'])!=plan['soul']['oldSha']:raise PermissionError('SOUL changed; rollback refused before replacing app/runtime')
    stage=Path(tempfile.mkdtemp(prefix='.Jarvis-rollback-',dir=p['app'].parent));restored=stage/'restored.app';shutil.copytree(original,restored)
    os.rename(p['app'],stage/'candidate.app')
    os.rename(restored,p['app']);restore_code(p['runtime'],backup)
    config=p['runtime']/'runtime-data/runtime-python.json';no_links(config,owner_from=p['runtime'])
    if (backup/'runtime-python.json').exists():shutil.copy2(backup/'runtime-python.json',config)
    elif config.exists():config.unlink()
    cua_config=p['runtime']/'runtime-data/runtime-cua.json';no_links(cua_config,owner_from=p['runtime'])
    if (backup/'runtime-cua.json').exists():shutil.copy2(backup/'runtime-cua.json',cua_config)
    elif cua_config.exists():cua_config.unlink()
    if 'soul' in plan:restore_soul(p,backup,plan)
    private_json(backup/'rollback-result.json',{'status':'restored-not-launched','retainedCandidate':str(stage/'candidate.app')})
    return {'status':'restored-not-launched','databaseReplacement':False,'credentialChanges':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');parser.add_argument('--reviewed-plan-sha256');parser.add_argument('--rollback');args=parser.parse_args();p=paths()
    if args.activate and args.rollback:raise ValueError('Choose activation or rollback')
    if args.rollback:result=rollback(p,args.rollback)
    elif args.activate:result=activate(p,args.reviewed_plan_sha256)
    else:
        plan=build_plan(p);result={'plan':plan,'reviewedPlanSha256':digest(plan),'activated':False}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
