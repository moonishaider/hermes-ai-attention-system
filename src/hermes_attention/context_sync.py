"""Owner-selected export folders, bounded reconciliation using reviewed importers.

A watched folder is a local standing import grant, not provider connectivity.
Removed local archives never imply remote source deletion or tombstone history.
"""
from datetime import date,datetime,UTC,timedelta
from hashlib import sha256
from pathlib import Path
import fcntl,json,os,stat,tempfile
from uuid import uuid4
from .history import ChatGPTExportImporter,GeminiTakeoutImporter

class ContextSync:
 def __init__(self,service,*,clock=None,importers=None):
  self.service=service;self.store=service.store;self.clock=clock or(lambda:datetime.now(UTC));self.importers=importers or {'chatgpt':ChatGPTExportImporter(self.store,service.router),'gemini':GeminiTakeoutImporter(self.store,service.router)}
  self.store.connection.executescript('''CREATE TABLE IF NOT EXISTS context_export_folders(folder_id TEXT PRIMARY KEY,path TEXT NOT NULL,source TEXT NOT NULL,start_date TEXT NOT NULL,enabled INTEGER NOT NULL,last_checked TEXT,next_check TEXT,last_result TEXT);CREATE TABLE IF NOT EXISTS context_export_files(folder_id TEXT NOT NULL,name TEXT NOT NULL,fingerprint TEXT NOT NULL,result_json TEXT NOT NULL,checked_at TEXT NOT NULL,PRIMARY KEY(folder_id,name));''')
 def status(self):
  rows=[]
  for row in self.store.connection.execute('SELECT * FROM context_export_folders'):
   item=dict(row);item['folder_name']=Path(item.pop('path')).name;item['last_result']=json.loads(item['last_result']) if item['last_result'] else None;rows.append(item)
  return {'folders':rows,'coverage':'Owner-selected official exports only; continuous provider sync unavailable','browser_extraction':False,'provider_writes':False}
 def register(self,path,source,start_date,*,owner_authorized=False):
  if not owner_authorized:raise PermissionError('Choose the exact export folder in the native owner interface')
  if source not in self.importers:raise ValueError('Choose ChatGPT or Gemini official exports')
  date.fromisoformat(start_date);folder=Path(path)
  if folder.is_symlink() or not folder.is_dir():raise ValueError('Select a real folder, not a symlink')
  folder=folder.resolve()
  existing=self.store.connection.execute('SELECT folder_id FROM context_export_folders WHERE path=? AND source=?',(str(folder),source)).fetchone()
  if existing:return {'folderId':existing[0],'status':'already-configured'}
  identity=str(uuid4())
  with self.store.connection:self.store.connection.execute('INSERT INTO context_export_folders VALUES(?,?,?,?,?,?,?,?)',(identity,str(folder),source,start_date,0,None,None,None))
  return {'folderId':identity,'status':'configured-off','folderName':folder.name}
 def enable(self,identity,enabled):
  if not isinstance(enabled,bool):raise ValueError('Expected explicit enable state')
  with self.store.connection:
   cursor=self.store.connection.execute('UPDATE context_export_folders SET enabled=?,next_check=NULL WHERE folder_id=?',(int(enabled),identity))
   if cursor.rowcount!=1:raise ValueError('Folder grant not found')
  return self.status()
 def remove(self,identity):
  with self.store.connection:
   self.store.connection.execute('DELETE FROM context_export_folders WHERE folder_id=?',(identity,));self.store.connection.execute('DELETE FROM context_export_files WHERE folder_id=?',(identity,))
  return self.status()
 def scan(self,identity=None,*,force=False):
  if self.store.database==':memory:':return self._scan(identity,force=force)
  lock_path=Path(self.store.database).parent/'.context-sync.lock'
  with lock_path.open('a') as lock:
   lock_path.chmod(0o600)
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return {'data':[],'status':'another-owned-scan-active'}
   try:return self._scan(identity,force=force)
   finally:fcntl.flock(lock,fcntl.LOCK_UN)
 def _scan(self,identity=None,*,force=False):
  results=[];budget=2;now=self.clock()
  rows=self.store.connection.execute('SELECT * FROM context_export_folders WHERE enabled=1').fetchall()
  for row in rows:
   if identity and row['folder_id']!=identity:continue
   if not force and row['next_check'] and datetime.fromisoformat(row['next_check'])>now:continue
   root=Path(row['path']);out={'folder_id':row['folder_id'],'source':row['source'],'status':'no-change','files':[],'provider_refresh':False};run_id=str(uuid4())
   with self.store.connection:self.store.connection.execute('INSERT INTO collection_runs VALUES(?,?,?,?,?,?,?,?,?)',(run_id,'export-folder:'+row['folder_id'],None,None,now.isoformat(),None,'running',0,None))
   directory=None
   try:
    if root.is_symlink() or not root.is_dir():raise ValueError('Approved export folder is unavailable')
    directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|getattr(os,'O_NOFOLLOW',0))
    candidates=[root/name for name in sorted(os.listdir(directory))[:100]]
    for path in candidates:
     if budget<=0:out['bounded']=True;break
     if path.suffix.lower() not in ({'.json','.zip'} if row['source']=='chatgpt' else {'.zip'}):continue
     descriptor=os.open(path.name,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0),dir_fd=directory)
     with os.fdopen(descriptor,'rb') as handle:
      info=os.fstat(handle.fileno())
      if not stat.S_ISREG(info.st_mode):continue
      if info.st_size>64*1024*1024:
       out['status']='failed' if out['status']=='failed' else 'partial';out['files'].append({'name':path.name,'status':'skipped-size-limit','error':'Export exceeds the 64 MiB folder-import limit; no data read from this file'});continue
      payload=handle.read(64*1024*1024+1)
     if len(payload)>64*1024*1024:raise ValueError('Export exceeds 64 MiB selected-folder limit')
     fingerprint=sha256(payload).hexdigest();previous=self.store.connection.execute('SELECT fingerprint,result_json FROM context_export_files WHERE folder_id=? AND name=?',(row['folder_id'],path.name)).fetchone()
     if previous and previous[0]==fingerprint and not(force and json.loads(previous[1]).get('status')=='failed'):
      prior=json.loads(previous[1])
      if prior.get('status')=='failed':out['status']='failed';out['files'].append({**prior,'retry':'Owner can retry this unchanged export explicitly'})
      continue
     budget-=1
     try:
      with tempfile.TemporaryDirectory(prefix='jarvis-export-') as temporary:
       snapshot=Path(temporary)/path.name;snapshot.write_bytes(payload);snapshot.chmod(0o600)
       importer=self.importers[row['source']];preview=importer.preview(snapshot,start_date=row['start_date']);receipt=importer.ingest(snapshot,start_date=row['start_date'],confirmed=True)
      result={'name':path.name,'status':'imported','preview':{key:value for key,value in preview.items() if key!='source'},'receipt':receipt};out['status']=out['status'] if out['status'] in {'failed','partial'} else 'updated'
     except Exception as error:result={'name':path.name,'status':'failed','error':str(error)[:200]};out['status']='failed'
     with self.store.connection:self.store.connection.execute('INSERT OR REPLACE INTO context_export_files VALUES(?,?,?,?,?)',(row['folder_id'],path.name,fingerprint,json.dumps(result),now.isoformat()))
     out['files'].append(result)
    if any(item['status']=='imported' for item in out['files']):self.service.refresh_work_ledger(limit=500)
   except Exception as error:out.update(status='failed',error=str(error)[:200])
   finally:
    if directory is not None:os.close(directory)
   with self.store.connection:
    self.store.connection.execute('UPDATE context_export_folders SET last_checked=?,next_check=?,last_result=? WHERE folder_id=?',(now.isoformat(),(now+timedelta(minutes=5)).isoformat(),json.dumps(out),row['folder_id']))
    self.store.connection.execute('UPDATE collection_runs SET finished_at=?,result=?,item_count=?,error_class=? WHERE run_id=?',(self.clock().isoformat(),out['status'],len(out['files']),'export-import' if out['status']=='failed' else None,run_id))
   results.append(out)
  return {'data':results,'bounded_files':2,'provider_refresh':False}
