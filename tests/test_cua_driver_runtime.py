import importlib.util,tempfile,unittest,json,hashlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('owned_driver',Path(__file__).resolve().parents[1]/'scripts/jarvis_cua_driver.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        (self.root/'.hermes-ai-attention-project').write_text('marker')
        binary=self.root/'computer-use/cua-driver-0.23.2/CuaDriver.app/Contents/MacOS/cua-driver';binary.parent.mkdir(parents=True);binary.write_bytes(b'signed-fixture')
        self.value={'enabled':False,'app':str(binary.parents[2]),'socket':str(self.root/'runtime-data/cua-driver.sock'),'stateDir':str(self.root/'runtime-data/cua-driver-state'),'binarySha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
        self.config=self.root/'runtime-data/runtime-cua.json';self.config.parent.mkdir();self.config.write_text(json.dumps(self.value));self.config.chmod(0o600)
    def test_owner_private_config_and_pinned_binary(self):
        value,binary=module.configuration(self.root);self.assertFalse(value['enabled'])
        Path(binary).write_bytes(b'changed')
        with self.assertRaises(PermissionError):module.configuration(self.root)
    def test_disabled_runtime_never_connects_or_launches(self):
        value,binary=module.configuration(self.root)
        with self.assertRaises(PermissionError):module.invocation(['mcp'],value,binary)
        self.assertEqual(module.invocation(['manifest'],value,binary),[binary,'manifest'])
    def test_explicit_socket_and_authority_overrides_rejected(self):
        value,binary=module.configuration(self.root);value['enabled']=True
        self.assertEqual(module.invocation(['mcp'],value,binary),[binary,'mcp','--socket',value['socket']])
        for args in [['mcp','--socket','foreign'],['mcp','--direct'],['mcp','--embedded'],['mcp','--grant=existing-profile'],['serve','--permission-mode','unrestricted']]:
            with self.subTest(args=args),self.assertRaises(PermissionError):module.invocation(args,value,binary)
    def test_world_readable_config_and_path_redirect_denied(self):
        self.config.chmod(0o644)
        with self.assertRaises(PermissionError):module.configuration(self.root)
        self.config.chmod(0o600);self.value['app']='/Applications/Other.app';self.config.write_text(json.dumps(self.value))
        with self.assertRaises(PermissionError):module.configuration(self.root)
if __name__=='__main__':unittest.main()
