import importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('companion_host',Path(__file__).resolve().parents[1]/'scripts/jarvis_companion.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class HostTests(unittest.TestCase):
 def test_no_listener_without_explicit_verified_transport(self):
  with tempfile.TemporaryDirectory() as directory:
   host=module.CompanionHost(Path(directory));self.assertFalse(host.status()['listening'])
   with self.assertRaises(PermissionError):host.start()
   self.assertEqual(host.start(owner_authorized=True)['state'],'transport-blocked');self.assertIsNone(host.server)
   with self.assertRaises(PermissionError):host.pair(owner_authorized=True)
   host.stop()
