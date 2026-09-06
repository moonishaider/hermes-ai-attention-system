"""Cleanup acceptance uses only disposable generated-file fixtures."""
import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cleanup_fixture',ROOT/'scripts/cleanup_jarvis_build_intermediates.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class CleanupTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();(self.root/'.hermes-ai-attention-project').touch()
  self.file=self.root/module.SUBROOTS[0]/'fixture.rlib';self.file.parent.mkdir(parents=True);self.file.write_bytes(b'synthetic compiler output')
 def manifest(self,path=None):
  p=path or self.file;return {'root':str(self.root),'files':[{'path':str(p.relative_to(self.root)),**module.identity(p)}]}
 def run_manifest(self,value,**kwargs):
  raw=json.dumps(value).encode();return module.execute(self.root,raw,hashlib.sha256(raw).hexdigest(),build_probe=lambda:False,**kwargs)
 def test_dry_run_keeps_every_byte_and_apply_deletes_only_fixture(self):
  value=self.manifest();other=self.file.with_name('keep.rlib');other.write_bytes(b'keep')
  result=self.run_manifest(value);self.assertEqual(result['deletedFiles'],0);self.assertTrue(self.file.exists())
  result=self.run_manifest(value,apply=True);self.assertEqual(result['deletedFiles'],1);self.assertFalse(self.file.exists());self.assertEqual(other.read_bytes(),b'keep');self.assertIn('freeSpaceDelta',result)
 def test_protected_bundle_traversal_and_duplicate_rejected(self):
  for name in ['jarvis/src-tauri/target/release/bundle/app.rlib','../owner.rlib','/tmp/owner.rlib']:
   value=self.manifest();value['files'][0]['path']=name
   with self.assertRaises(ValueError):self.run_manifest(value,apply=True)
  value=self.manifest();value['files']*=2
  with self.assertRaises(ValueError):self.run_manifest(value)
  self.assertTrue(self.file.exists())
 def test_hardlink_and_leaf_symlink_rejected(self):
  value=self.manifest();self.file.with_name('linked').hardlink_to(self.file)
  with self.assertRaises(ValueError):self.run_manifest(value,apply=True)
  self.file.with_name('linked').unlink();self.file.unlink();target=self.root/'owner';target.write_bytes(b'owner');self.file.symlink_to(target)
  with self.assertRaises(ValueError):self.run_manifest(value,apply=True)
  self.assertEqual(target.read_bytes(),b'owner')
 def test_ancestor_symlink_rejected(self):
  value=self.manifest();self.file.unlink();self.file.parent.rmdir();outside=self.root/'other';outside.mkdir();(outside/self.file.name).write_bytes(b'owner');self.file.parent.symlink_to(outside,target_is_directory=True)
  with self.assertRaises(ValueError):self.run_manifest(value,apply=True)
 def test_changed_content_and_wrong_digest_rejected(self):
  value=self.manifest();self.file.write_bytes(b'changed compiler output')
  with self.assertRaises(ValueError):self.run_manifest(value,apply=True)
  with self.assertRaises(ValueError):module.execute(self.root,json.dumps(value).encode(),'incorrect',build_probe=lambda:False)
 def test_active_build_refused(self):
  raw=json.dumps(self.manifest()).encode()
  with self.assertRaises(ValueError):module.execute(self.root,raw,hashlib.sha256(raw).hexdigest(),apply=True,build_probe=lambda:True)
  self.assertTrue(self.file.exists())
 def test_swapped_object_at_rename_is_retained_never_deleted(self):
  value=self.manifest();rename=module.os.rename
  def swap(source,destination,**kwargs):
   source.unlink();source.write_bytes(b'UNREVIEWED replacement');rename(source,destination,**kwargs)
  with patch.object(module.os,'rename',side_effect=swap):
   with self.assertRaises(ValueError):self.run_manifest(value,apply=True)
  stages=list((self.root/'jarvis/src-tauri/target').glob('.reviewed-cleanup-*'))
  self.assertEqual((stages[0]/'0').read_bytes(),b'UNREVIEWED replacement')
  self.assertIn('before-move',(stages[0]/'journal.jsonl').read_text())

 def test_stage_path_swap_does_not_redirect_delete_to_replacement(self):
  value=self.manifest();rename=module.os.rename;victim=self.root/'untouched';victim.mkdir();(victim/'0').write_bytes(b'owner bytes');redirected=False
  def redirect(source,destination,**kwargs):
   nonlocal redirected
   if kwargs.get('dst_dir_fd') is not None and not redirected:
    redirected=True;stage=next((self.root/'jarvis/src-tauri/target').glob('.reviewed-cleanup-*'));rename(stage,stage.with_name(stage.name+'-retained'));stage.symlink_to(victim,target_is_directory=True)
   rename(source,destination,**kwargs)
  with patch.object(module.os,'rename',side_effect=redirect):result=self.run_manifest(value,apply=True)
  self.assertEqual(result['deletedFiles'],1);self.assertEqual((victim/'0').read_bytes(),b'owner bytes')
