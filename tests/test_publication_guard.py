"""Publication policy tests use isolated repositories and synthetic payloads."""
import importlib.util
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('candidate_scan',ROOT/'scripts/secret_scan.py')
scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
class CandidateTests(unittest.TestCase):
    def test_normal_code(self): self.assertIsNone(scan.inspect('src/example.py',b'answer = 42\n'))
    def test_private_and_large_and_symlink(self):
        for name,data,mode in [('runtime-data/private.txt',b'x','100644'),('sample.txt',b'x'*(scan.MAX_BYTES+1),'100644'),('src/a',b'../../secret','120000')]:
            self.assertIsNotNone(scan.inspect(name,data,mode))
    def test_committed_secret_not_hidden_by_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def git(*args): return subprocess.run(['git','-C',tmp,*args],check=True,capture_output=True)
            git('init');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
            p=root/'example.py';p.write_text('token = "'+'ghp_'+'a'*40+'"\n');git('add','example.py');git('commit','-m','synthetic fixture')
            p.write_text('safe = True\n')
            self.assertEqual(scan.scan_commits(root,['HEAD'])[0][0],'example.py')
    def test_push_wrapper_rejects_wrong_remote_branch_and_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); scripts=root/'scripts'; scripts.mkdir(); bins=root/'bin';bins.mkdir()
            shutil.copy2(ROOT/'scripts/safe_git_push.sh',scripts/'safe_git_push.sh')
            (scripts/'preflight_safety.sh').write_text('#!/bin/sh\nexit 0\n');(scripts/'preflight_safety.sh').chmod(0o755)
            fake = """#!/usr/bin/env python3
import os,sys
args=sys.argv[1:]
if args[:1]==['-C']: args=args[2:]
if args[:2]==['remote','get-url']:
 print(os.environ.get('PUSH_URL') if '--push' in args else 'https://github.com/moonishaider/hermes-ai-attention-system.git')
elif args[:1]==['symbolic-ref']: print('main')
elif args[:1]==['rev-parse']: print('a'*40)
elif args[:1]==['check-ref-format']: pass
elif args[:1]==['api']: print('moonishaider')
elif args[:2]==['repo','view']: print(os.environ.get('REPO_META','moonishaider/hermes-ai-attention-system PUBLIC'))
else: sys.exit(93)
"""
            for name in ['git','gh']:
                p=bins/name;p.write_text(fake);p.chmod(0o755)
            env=dict(os.environ,PATH=str(bins)+os.pathsep+os.environ['PATH'],PUSH_URL='https://github.com/moonishaider/hermes-ai-attention-system.git')
            cases=[({'PUSH_URL':'https://github.com/moonishaider/hermes-ai-attention-system-evil.git'},'main','alternate remote'),({},'other','Reviewed branch'),({'REPO_META':'moonishaider/hermes-ai-attention-system PRIVATE'},'main','PUBLIC visibility')]
            for delta,branch,message in cases:
                result=subprocess.run(['bash',str(scripts/'safe_git_push.sh'),'origin',branch,'a'*40],env=dict(env,**delta),capture_output=True,text=True)
                self.assertEqual(result.returncode,1,result.stderr);self.assertIn(message,result.stderr)
    def test_guard_contract(self):
        script=(ROOT/'scripts/safe_git_push.sh').read_text()
        self.assertNotIn('hermes-ai-attention-system*',script)
        for boundary in ['--push --all origin','REVIEWED_BRANCH','REVIEWED_SHA','PUBLIC','merge-base --is-ancestor','scan','refs/heads/$BRANCH']:
            self.assertIn(boundary,script)
if __name__=='__main__': unittest.main()
