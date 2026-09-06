import unittest
import os,sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from hermes_attention.install_guard import inspect_install,NAMES,first_database_backup,companion_manifest,install_companion_assets
class InstallGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'project';self.root.mkdir();self.home=Path(self.temp.name).resolve()/'home';self.home.mkdir()
        for name in NAMES:
            path=self.root/name
            if name.startswith('.hermes-ai'):path.write_text('marker')
            else:path.mkdir()
    def tearDown(self):self.temp.cleanup()
    def test_existing_runtime_and_state_are_preserved(self):
        runtime=self.home/'.hermes/jarvis-runtime';(runtime/'runtime-data').mkdir(parents=True)
        (runtime/'.hermes-ai-attention-project').write_text('marker')
        db=runtime/'runtime-data/hermes_attention.sqlite3';db.write_bytes(b'original')
        result=inspect_install(self.root,self.home)
        self.assertFalse(result['database_replace']);self.assertEqual(db.read_bytes(),b'original')
    def test_redirected_runtime_cannot_receive_writes(self):
        (self.home/'.hermes').mkdir();(self.home/'.hermes/jarvis-runtime').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):inspect_install(self.root,self.home)
    def test_unrelated_plugin_rejected_before_install(self):
        links=self.home/'.hermes/plugins';links.mkdir(parents=True);(links/'hermes-attention').symlink_to(self.root/'unrelated')
        with self.assertRaises(ValueError):inspect_install(self.root,self.home)
        self.assertFalse((self.home/'.hermes/jarvis-runtime').exists())
    def test_source_symlink_cannot_escape(self):
        (self.root/'src/escape').symlink_to(self.home,target_is_directory=True)
        with self.assertRaises(ValueError):inspect_install(self.root,self.home)
    def test_unmarked_existing_runtime_denied(self):
        (self.home/'.hermes/jarvis-runtime').mkdir(parents=True)
        with self.assertRaises(ValueError):inspect_install(self.root,self.home)
    def test_special_source_denied(self):
        os.mkfifo(self.root/'src/pipe')
        with self.assertRaises(ValueError):inspect_install(self.root,self.home)
    def test_source_database_symlink_denied(self):
        (self.root/'runtime-data').mkdir()
        (self.root/'runtime-data/hermes_attention.sqlite3').symlink_to(self.home/'secret')
        with self.assertRaises(ValueError):inspect_install(self.root,self.home)
    def test_database_backup_includes_wal_and_never_overwrites(self):
        src=self.root/'source.sqlite';dst=self.root/'copy.sqlite'
        db=sqlite3.connect(src);db.execute('pragma journal_mode=wal');db.execute('create table sample(value)');db.execute('insert into sample values (42)');db.commit()
        first_database_backup(src,dst)
        with sqlite3.connect(dst) as copy:self.assertEqual(copy.execute('select value from sample').fetchone()[0],42)
        with self.assertRaises(ValueError):first_database_backup(src,dst)
        db.close()
    def test_companion_mirrors_only_hashed_dist_and_preserves_old_assets(self):
        dist=self.root/'jarvis/dist';dist.mkdir(parents=True);(dist/'index.html').write_text('compiled');(dist/'assets').mkdir();(dist/'assets/main.js').write_text('compiled js')
        (self.root/'jarvis/private.txt').write_text('do not copy')
        runtime=self.home/'.hermes/jarvis-runtime';runtime.mkdir(parents=True);(runtime/'.hermes-ai-attention-project').write_text('marker')
        (runtime/'companion-web').mkdir();(runtime/'companion-web/old.js').write_text('preserve')
        manifest=companion_manifest(self.root);result=install_companion_assets(self.root,self.home)
        self.assertEqual(result['assetSha256'],manifest['sha256']);self.assertTrue((runtime/'companion-web/assets/main.js').is_file())
        self.assertFalse((runtime/'companion-web/private.txt').exists());self.assertFalse((runtime/'companion-web/old.js').exists())
        self.assertEqual((Path(result['previous'])/'old.js').read_text(),'preserve')
    def test_companion_private_or_symlink_inputs_rejected(self):
        dist=self.root/'jarvis/dist';dist.mkdir(parents=True);(dist/'index.html').write_text('compiled');(dist/'.env').write_text('private')
        with self.assertRaises(ValueError):companion_manifest(self.root)
        (dist/'.env').unlink();(dist/'escape.js').symlink_to(self.home/'outside.js')
        with self.assertRaises(ValueError):companion_manifest(self.root)
if __name__=='__main__':unittest.main()
