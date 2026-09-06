"""Readable task/standing grants; trusted owner intent is outside model arguments."""
from datetime import datetime,UTC,timedelta
import json
from uuid import uuid4
from .domain import utc_now

OPERATIONS={'browser.read','browser.navigate','browser.form','browser.download','apps.open',
 'calendar.create','calendar.update','calendar.undo','draft.create','draft.read','draft.update',
 'files.analyze','artifacts.create','memory.preference','skills.edit','jobs.local','finance.prepare'}
COMPANY_READ={'browser.read'}

def ensure_schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS personal_grants(grant_id TEXT PRIMARY KEY,title TEXT NOT NULL,context_id TEXT NOT NULL,account_id TEXT NOT NULL,profile TEXT NOT NULL,operations_json TEXT NOT NULL,domains_json TEXT NOT NULL,apps_json TEXT NOT NULL,resources_json TEXT NOT NULL,standing INTEGER NOT NULL,expires_at TEXT NOT NULL,status TEXT NOT NULL,last_used TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS personal_capability_stops(capability TEXT PRIMARY KEY,stopped INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS personal_grant_audit(audit_id TEXT PRIMARY KEY,grant_id TEXT NOT NULL,operation TEXT NOT NULL,result TEXT NOT NULL,detail_json TEXT NOT NULL,created_at TEXT NOT NULL);
    ''')

def assert_operation_running(store, operation):
    """Shared emergency stop gate; independent of grants and legacy capability IDs.

    Older stores without the additive permissions tables have no recorded stops.
    Do not run schema migrations here: checks must not commit an execution claim.
    """
    conn=store.connection
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_capability_stops'").fetchone():
        return
    if conn.execute("SELECT 1 FROM personal_capability_stops WHERE capability IN ('all',?) AND stopped=1",(operation,)).fetchone():
        raise PermissionError('capability emergency stop active')

class Permissions:
    def __init__(self,store,*,authorize_owner=None,clock=None):
        self.store=store;self.owner=authorize_owner or (lambda op,resource:False);self.clock=clock or (lambda:datetime.now(UTC));ensure_schema(store.connection)
    def _owner(self,operation,resource):
        if self.owner(operation,resource) is not True:raise PermissionError('trusted owner authorization required')
    def issue(self,*,title,context_id,account_id,profile,operations,domains=None,apps=None,resources=None,standing=False,hours=12):
        value=locals().copy();value.pop('self');self._owner('grant',value)
        if not title or not account_id or not profile:raise ValueError('readable title, exact account and profile required')
        if not operations or set(operations)-OPERATIONS:raise PermissionError('unsupported or consequential operation')
        if context_id!='personal' and set(operations)-COMPANY_READ:raise PermissionError('company/client tasks are read-only')
        if not 0<hours<=(2160 if standing else 24):raise ValueError('grant duration exceeds bounded lifetime')
        domains=domains or [];apps=apps or [];resources=resources or []
        if any('/' in d or ':' in d or d.startswith('.') or '*' in d for d in domains):raise ValueError('domains must be exact hostnames')
        gid=str(uuid4());now=self.clock();expires=(now+timedelta(hours=hours)).isoformat()
        with self.store.connection:self.store.connection.execute('INSERT INTO personal_grants VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(gid,title,context_id,account_id,profile,json.dumps(sorted(set(operations))),json.dumps(domains),json.dumps(apps),json.dumps(resources),int(standing),expires,'active',None,now.isoformat()))
        return self.get(gid)
    def get(self,grant_id):
        row=self.store.connection.execute('SELECT * FROM personal_grants WHERE grant_id=?',(grant_id,)).fetchone()
        if not row:raise PermissionError('grant not found')
        value=dict(row)
        for name in ('operations','domains','apps','resources'):value[name]=json.loads(value.pop(name+'_json'))
        value['expired']=datetime.fromisoformat(value['expires_at'])<=self.clock()
        return value
    def list(self):return [self.get(r[0]) for r in self.store.connection.execute('SELECT grant_id FROM personal_grants ORDER BY created_at DESC')]
    def revoke(self,grant_id):
        self._owner('revoke',grant_id)
        with self.store.connection:self.store.connection.execute("UPDATE personal_grants SET status='revoked' WHERE grant_id=?",(grant_id,))
    def stop(self,capability,stopped=True):
        if capability!='all' and capability not in OPERATIONS:raise ValueError('unknown capability')
        self._owner('stop' if stopped else 'resume',capability)
        with self.store.connection:self.store.connection.execute('INSERT OR REPLACE INTO personal_capability_stops VALUES(?,?)',(capability,int(stopped)))
    def check(self,grant_id,operation,*,context_id,account_id,profile,domain=None,app=None,resource=None):
        grant=self.get(grant_id)
        if grant['status']!='active' or grant['expired']:raise PermissionError('grant revoked or expired')
        assert_operation_running(self.store,operation)
        if operation not in grant['operations']:raise PermissionError('operation was not granted')
        if (context_id,account_id,profile)!=(grant['context_id'],grant['account_id'],grant['profile']):raise PermissionError('account, context or browser profile changed')
        if domain and grant['domains'] and domain not in grant['domains']:raise PermissionError('domain is outside task grant')
        if app and app not in grant['apps']:raise PermissionError('application is outside task grant')
        if resource and resource not in grant['resources']:raise PermissionError('resource is outside task grant')
        with self.store.connection:self.store.connection.execute('UPDATE personal_grants SET last_used=? WHERE grant_id=?',(utc_now(),grant_id))
        return grant
    def audit(self,grant_id,operation,result,detail):
        with self.store.connection:self.store.connection.execute('INSERT INTO personal_grant_audit VALUES(?,?,?,?,?,?)',(str(uuid4()),grant_id,operation,result,json.dumps(detail),utc_now()))
