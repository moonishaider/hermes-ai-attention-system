import importlib.util,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('candidate_activation',Path(__file__).resolve().parents[1]/'scripts/activate_jarvis_candidate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ActivationTests(unittest.TestCase):
    def test_plan_digest_binds_code_dependency_app_and_interpreter(self):
        plan={'newAppSha':'one','dependencySha':'deps','finalPython':'owned/python','sourceCode':{'src':'source'}}
        expected=module.digest(plan)
        for key in plan:
            with self.subTest(key=key):self.assertNotEqual(expected,module.digest({**plan,key:'changed'}))
    def test_wrong_digest_cannot_create_or_run_anything(self):
        with patch.object(module,'build_plan',return_value={'review':'exact'}),patch.object(module,'require_stopped') as stopped,patch.object(module.subprocess,'run') as run:
            with self.assertRaises(PermissionError):module.activate({},'wrong')
            stopped.assert_not_called();run.assert_not_called()
    def test_symlink_bundle_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'bundle').mkdir();(root/'bundle/alias').symlink_to(root/'outside')
            with self.assertRaises(ValueError):module.tree(root/'bundle')
    def test_private_config_is_atomic_private_and_rejects_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();path=root/'runtime-python.json';module.private_json(path,{'python':'owned/python'})
            self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(json.loads(path.read_text())['python'],'owned/python')
            link=root/'link';link.symlink_to(path)
            with self.assertRaises(ValueError):module.private_json(link,{'python':'bad'})
    def test_code_snapshot_excludes_operational_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();runtime=root/'runtime';backup=root/'backup';runtime.mkdir();backup.mkdir()
            (runtime/'src').mkdir();(runtime/'src/a.py').write_text('source')
            (runtime/'runtime-data').mkdir();(runtime/'runtime-data/db').write_text('private state')
            module.code_backup(runtime,backup)
            self.assertEqual((backup/'runtime-code/src/a.py').read_text(),'source');self.assertFalse((backup/'runtime-code/runtime-data').exists())
    def test_receipt_disk_failure_restores_original_app_code_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve();runtime=home/'runtime';runtime.mkdir();(runtime/'src').mkdir();(runtime/'src/code').write_text('old')
            (runtime/'runtime-data').mkdir();(runtime/'runtime-data/state.db').write_text('preserve')
            app=home/'Jarvis.app';app.mkdir();(app/'binary').write_text('old-app')
            built=home/'built.app';built.mkdir();(built/'binary').write_text('new-app')
            candidate=home/'candidate';candidate.mkdir();(candidate/'freeze.txt').write_text('')
            p={'home':home,'root':home,'runtime':runtime,'app':app,'built':built,'candidate':candidate,'backup_root':home/'backups','final_env':runtime/'python-envs/v1','bundled':home/'python'}
            driver=home/'driver.app';(driver/'Contents/MacOS').mkdir(parents=True);(driver/'Contents/MacOS/cua-driver').write_text('signed fixture')
            p.update(driver_source=driver,driver_target=runtime/'computer-use/cua-driver-0.23.2/CuaDriver.app')
            (home/'.hermes').mkdir();(home/'.hermes/SOUL.md').write_text('old-policy');(home/'hermes').mkdir();(home/'hermes/SOUL.md').write_text('new-policy');(runtime/'hermes').mkdir();(runtime/'hermes/SOUL.md').write_text('old-policy')
            plan={'soul':module.soul_plan(p),'newAppSha':module.tree(built),'driverAppSha':module.tree(driver)};real_run=module.subprocess.run;real_json=module.private_json;failed=[]
            def run(args,**kwargs):
                if '-m' in args and 'venv' in args:
                    (p['final_env']/'bin').mkdir(parents=True);(p['final_env']/'bin/python').write_text('fixture')
                elif args[0]=='/bin/bash':
                    (runtime/'src/code').write_text('new');(runtime/'src/new-file').write_text('keep-for-inspection')
                elif args[0]=='/usr/bin/rsync':return real_run(args,**kwargs)
            def write(path,value):
                if path.name=='activation-result.json' and not failed:failed.append(True);raise OSError('simulated receipt disk failure')
                return real_json(path,value)
            with patch.object(module,'build_plan',return_value=plan),patch.object(module,'require_stopped'),patch.object(module,'signature',return_value='verified fixture'),patch.object(module.subprocess,'run',side_effect=run),patch.object(module,'private_json',side_effect=write):
                with self.assertRaises(OSError):module.activate(p,module.digest(plan))
            self.assertEqual((home/'.hermes/SOUL.md').read_text(),'old-policy')
            self.assertEqual((app/'binary').read_text(),'old-app');self.assertEqual((runtime/'src/code').read_text(),'old')
            self.assertEqual((runtime/'runtime-data/state.db').read_text(),'preserve');self.assertFalse((runtime/'runtime-data/runtime-python.json').exists())
            preserved=list((home/'backups').glob('*/failed-runtime-code-*/src/new-file'))
            self.assertEqual(len(preserved),1);self.assertEqual(preserved[0].read_text(),'keep-for-inspection')
class EnvironmentReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);home=Path(self.tmp.name).resolve();runtime=home/'runtime';candidate=home/'candidate';candidate.mkdir();(candidate/'freeze.txt').write_text('example==1.0\n')
        self.p={'home':home,'runtime':runtime,'candidate':candidate,'backup_root':home/'backups','final_env':runtime/'python-envs/v1'}
        self.python=self.p['final_env']/'bin/python';self.python.parent.mkdir(parents=True);self.python.write_text('fixture');self.python.chmod(0o700)
        receipt=self.p['backup_root']/'jarvis-candidate-before-test';receipt.mkdir(parents=True)
        self.plan={'dependencySha':module.sha(candidate/'freeze.txt'),'finalPython':str(self.python),'runtime':str(runtime)}
        module.private_json(receipt/'activation-plan.json',self.plan)
        module.private_json(receipt/'activation-result.json',{'status':'installed-not-launched','python':str(self.python)})
        (runtime/'runtime-data').mkdir();self.config=runtime/'runtime-data/runtime-python.json'
        module.private_json(self.config,{'python':str(self.python),'candidateReceipt':str(receipt/'activation-plan.json')})
    def test_exact_activated_environment_reused_without_install(self):
        with patch.object(module.subprocess,'check_output',return_value='example==1.0\n'),patch.object(module.subprocess,'run') as run:
            self.assertEqual(module.verify_reusable_environment(self.p,self.plan),self.python)
            self.assertEqual(len(run.call_args_list),2)
            self.assertTrue(all('install' not in call.args[0] and 'venv' not in call.args[0] for call in run.call_args_list))
    def test_package_drift_refused_before_checks_or_installs(self):
        with patch.object(module.subprocess,'check_output',return_value='example==2.0\n'),patch.object(module.subprocess,'run') as run:
            with self.assertRaises(PermissionError):module.verify_reusable_environment(self.p,self.plan)
            run.assert_not_called()
    def test_stale_receipt_or_selected_path_refused_before_execution(self):
        with patch.object(module.subprocess,'check_output') as execute:
            with self.assertRaises(PermissionError):module.verify_reusable_environment(self.p,{**self.plan,'dependencySha':'different'})
            value=json.loads(self.config.read_text());value['python']=str(self.python.parent/'foreign');module.private_json(self.config,value)
            with self.assertRaises(PermissionError):module.verify_reusable_environment(self.p,self.plan)
            execute.assert_not_called()
    def test_unowned_receipt_location_and_interpreter_link_refused(self):
        value=json.loads(self.config.read_text());value['candidateReceipt']=str(self.p['home']/'arbitrary-plan.json');module.private_json(self.config,value)
        with self.assertRaises(PermissionError):module.verify_reusable_environment(self.p,self.plan)
        self.python.rename(self.python.with_name('actual'));self.python.symlink_to(self.python.with_name('actual'))
        with self.assertRaises(ValueError):module.verify_reusable_environment(self.p,self.plan)
class SoulActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);home=Path(self.tmp.name).resolve()
        self.p={'home':home,'root':home/'project','runtime':home/'runtime'}
        self.active=home/'.hermes/SOUL.md';self.desired=self.p['root']/'hermes/SOUL.md';self.previous=self.p['runtime']/'hermes/SOUL.md'
        for path,text in [(self.active,'old'),(self.previous,'old'),(self.desired,'new')]:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        self.backup=home/'backup';self.backup.mkdir();(self.backup/'SOUL.md').write_text('old')
    def test_exact_sync_and_restore_only_policy(self):
        plan={'soul':module.soul_plan(self.p)};sentinel=self.active.parent/'config.yaml';sentinel.write_text('preserve')
        module.replace_soul(self.desired,self.active,plan['soul']['oldSha'],self.p['home'])
        self.assertEqual(self.active.read_text(),'new')
        module.restore_soul(self.p,self.backup,plan)
        self.assertEqual(self.active.read_text(),'old');self.assertEqual(sentinel.read_text(),'preserve')
    def test_independent_active_change_refuses_plan_and_rollback(self):
        plan={'soul':module.soul_plan(self.p)};self.active.write_text('owner revised')
        with self.assertRaises(PermissionError):module.soul_plan(self.p)
        with self.assertRaises(PermissionError):module.restore_soul(self.p,self.backup,plan)
        self.assertEqual(self.active.read_text(),'owner revised')
    def test_link_and_modified_backup_refused(self):
        plan={'soul':module.soul_plan(self.p)};self.active.unlink();self.active.symlink_to(self.previous)
        with self.assertRaises(ValueError):module.soul_plan(self.p)
        self.active.unlink();self.active.write_text('new');(self.backup/'SOUL.md').write_text('modified')
        with self.assertRaises(PermissionError):module.restore_soul(self.p,self.backup,plan)
        self.assertEqual(self.active.read_text(),'new')

if __name__=='__main__':unittest.main()
