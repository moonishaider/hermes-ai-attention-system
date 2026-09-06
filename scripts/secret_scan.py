#!/usr/bin/env python3
"""Fail-closed candidate scanner. Publication scans Git blobs, never worktree substitutes."""
from pathlib import Path
import argparse
import hashlib
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hermes_attention.security import SECRET_PATTERNS
MAX_BYTES = 2_000_000
# Existing committed application icon bytes; changes require explicit review.
REVIEWED_ASSETS = {'jarvis/src-tauri/icons/128x128.png': '02bd08dce978b33de91f47954bbdc28757fef8af04604a3c68a9585c90a44bd4',
 'jarvis/src-tauri/icons/128x128@2x.png': 'a554b75d7e11733aba5c6c14db3d34ceeed42586a6441c9ade8df12b1fca4977',
 'jarvis/src-tauri/icons/32x32.png': 'ea660b056e60a74d8755bfabb79768a0303643a18ea2b73ce68acdd35c8150c1',
 'jarvis/src-tauri/icons/64x64.png': '7e5133f26556b56169d9871d5f998cca7ce5b0ff4c2079223b5a1673760d0dcc',
 'jarvis/src-tauri/icons/Square107x107Logo.png': '3f08dbc32ba58c6dd407ba4f9c547483aa2bbaede798002453d293c1e8008887',
 'jarvis/src-tauri/icons/Square142x142Logo.png': '57f17ca669fefd29bc4fb3d539752d65a3b03a4bd2424fa3ae18669bf45fb5a4',
 'jarvis/src-tauri/icons/Square150x150Logo.png': '124e773c2b8e6899c530214ed64837728951dbeea94a22dd14114a28bda6ad40',
 'jarvis/src-tauri/icons/Square284x284Logo.png': '2aaf87fd02838246bca04682f39aecb702d16c33eceb54847acb8391ba3fd931',
 'jarvis/src-tauri/icons/Square30x30Logo.png': 'd1709232727995098b6df7d1d792436b261fb5c9e96536559c1d4bb2a143e8e6',
 'jarvis/src-tauri/icons/Square310x310Logo.png': 'a9b580bb288e3e8062738f96d222a04f4744a90fe6371468d1ac87c6ce4bbe54',
 'jarvis/src-tauri/icons/Square44x44Logo.png': 'c84fe4651c471fa8e8dbeb8d5a5e53961daf6690792f5cd287d6ea4559808129',
 'jarvis/src-tauri/icons/Square71x71Logo.png': '8c8b1f215b4695188ff9a707978dd38badebdd57147eedcdfd90a83c2e66876d',
 'jarvis/src-tauri/icons/Square89x89Logo.png': '054c8908e92b3847aa8aa984c27e0cfed149242b27c54c53782d349f768df6c5',
 'jarvis/src-tauri/icons/StoreLogo.png': '5cbee4289618de069e821e997c8b6ef49f1e658dde930c10f108e95034b5eae8',
 'jarvis/src-tauri/icons/android/mipmap-anydpi-v26/ic_launcher.xml': '760d4b8a06bf7163dd010c33ad2cac9e4a75fa0177afaba042f83e311eef0c3e',
 'jarvis/src-tauri/icons/android/mipmap-hdpi/ic_launcher.png': '9d28f54424d04ba1ddbc01a1ab399b599503cef52097125426790d7979a77f9b',
 'jarvis/src-tauri/icons/android/mipmap-hdpi/ic_launcher_foreground.png': 'c66372b16f7696f1ed46ac561629ef176934b8e0440e6234efd85a6f4d874d10',
 'jarvis/src-tauri/icons/android/mipmap-hdpi/ic_launcher_round.png': '1a1955f618f3df8488af96979f07dd9370747be6120e06f6a2d0d011c9d84ead',
 'jarvis/src-tauri/icons/android/mipmap-mdpi/ic_launcher.png': '523808db2d3639d7c64b545af42610f7c7779565b4f81a8800ec6ad92010c155',
 'jarvis/src-tauri/icons/android/mipmap-mdpi/ic_launcher_foreground.png': '75f9ebd580874ce9e22b66a1349e1ca0a5db7144d0741ffc7c04755cd2ec1fa5',
 'jarvis/src-tauri/icons/android/mipmap-mdpi/ic_launcher_round.png': '7faabd4ba0a1302ff46ca13db243e71d7292f107a2e6056869dfc4cddde67798',
 'jarvis/src-tauri/icons/android/mipmap-xhdpi/ic_launcher.png': '422e2bce12cbe36fb321c9ee42682658542ec0cf0a396c12cd632e5b57cb5d66',
 'jarvis/src-tauri/icons/android/mipmap-xhdpi/ic_launcher_foreground.png': '77290100ff3e6dfd9b5e7c445e34168d619439e89745cf01e12e932be7afdc6c',
 'jarvis/src-tauri/icons/android/mipmap-xhdpi/ic_launcher_round.png': 'd209d03cf58341fdcf3e23fb2ffe80797c7c64d9463624c81be3517b5ba533dc',
 'jarvis/src-tauri/icons/android/mipmap-xxhdpi/ic_launcher.png': '2377d52e455d3c5a858f4ef956ba74e13bdb7f8451adf61924a71c1684de5e58',
 'jarvis/src-tauri/icons/android/mipmap-xxhdpi/ic_launcher_foreground.png': 'b79fb25c1df6adce3648af87cb8a3ec05891c9be113866dfd075ecd8cc297c80',
 'jarvis/src-tauri/icons/android/mipmap-xxhdpi/ic_launcher_round.png': '0dc92755b75ea51fdd673865bd92579a305c4fc609403f7c87da175428122b15',
 'jarvis/src-tauri/icons/android/mipmap-xxxhdpi/ic_launcher.png': 'c45594cbd9fcdee8f353a3416b69f855fffe1a54b34e5e7858642c33072e0676',
 'jarvis/src-tauri/icons/android/mipmap-xxxhdpi/ic_launcher_foreground.png': '6ea651868cf69ca43252b24fa20980eeabbd684fd00ca0aef440b23f139b63b0',
 'jarvis/src-tauri/icons/android/mipmap-xxxhdpi/ic_launcher_round.png': 'a03ae37b168b6c5fc968ff918553924ce2aab3fa31ec66c001c4bac4f68f951c',
 'jarvis/src-tauri/icons/android/values/ic_launcher_background.xml': '0687336f0ccc6f7ee09c7c95110667c63b75931238df779a21af401fb864cd34',
 'jarvis/src-tauri/icons/icon.icns': '59aae3fc5a6840c378ecb04aa5457106f529525feea03ed2d16d14c9faee093b',
 'jarvis/src-tauri/icons/icon.ico': '2ff7c57fa56c81a8a4e1473a87b10e60f3ff2f27642c56ef46a3ea02559dba5b',
 'jarvis/src-tauri/icons/icon.png': 'ccc924ff1ee134a9af9e4b4ebce01d38db4a10b0b3622d34b183b29fbaa64897',
 'jarvis/src-tauri/icons/ios/AppIcon-20x20@1x.png': '6b1e8d856caf5012cf5aa8fdd70ea32122af89d1f7c69adc7d64cc49a7caea35',
 'jarvis/src-tauri/icons/ios/AppIcon-20x20@2x-1.png': 'ca9694a685264ab66f5ed8a85e020340c553325284207080f6542ea5c962ed28',
 'jarvis/src-tauri/icons/ios/AppIcon-20x20@2x.png': 'ca9694a685264ab66f5ed8a85e020340c553325284207080f6542ea5c962ed28',
 'jarvis/src-tauri/icons/ios/AppIcon-20x20@3x.png': '5950e0b90dd5badff2eddec6b86d4a65b87a41d091c8388cf15cd59a43398a7a',
 'jarvis/src-tauri/icons/ios/AppIcon-29x29@1x.png': '22c4c422c0f37ea2b596c8d7966eb42771bc90ec4a3eb3c5759a1a676971f2e9',
 'jarvis/src-tauri/icons/ios/AppIcon-29x29@2x-1.png': 'b80f6a518d09f344cde3eee40012b4c8a2de89b2c9d9443f0e410aa01fa3a957',
 'jarvis/src-tauri/icons/ios/AppIcon-29x29@2x.png': 'b80f6a518d09f344cde3eee40012b4c8a2de89b2c9d9443f0e410aa01fa3a957',
 'jarvis/src-tauri/icons/ios/AppIcon-29x29@3x.png': '76193b979bef0358be00edad863ff4d2379e799b551ceddb12adb81b3ac15110',
 'jarvis/src-tauri/icons/ios/AppIcon-40x40@1x.png': 'ca9694a685264ab66f5ed8a85e020340c553325284207080f6542ea5c962ed28',
 'jarvis/src-tauri/icons/ios/AppIcon-40x40@2x-1.png': '77786e48f44c85305fc7de9fab283769830a0411e73ecc9f262ef1bccac0048e',
 'jarvis/src-tauri/icons/ios/AppIcon-40x40@2x.png': '77786e48f44c85305fc7de9fab283769830a0411e73ecc9f262ef1bccac0048e',
 'jarvis/src-tauri/icons/ios/AppIcon-40x40@3x.png': '00968d4be9b048daa400578ae0c5526488a1770dacd32edd8308f62859bd81fb',
 'jarvis/src-tauri/icons/ios/AppIcon-512@2x.png': '647eec14f699fa81a0a3f05facbce9dca5ce64c3cb749eb1aafb807332abc8cb',
 'jarvis/src-tauri/icons/ios/AppIcon-60x60@2x.png': '00968d4be9b048daa400578ae0c5526488a1770dacd32edd8308f62859bd81fb',
 'jarvis/src-tauri/icons/ios/AppIcon-60x60@3x.png': 'd5ff063bf3bd9fec3a12600c07f5dacffbf013c815f2896fd0a6a6168835c515',
 'jarvis/src-tauri/icons/ios/AppIcon-76x76@1x.png': '55dee9ef0cc3a94333091904f380c55cfdb7942cfd83ab7ece96d4870098f272',
 'jarvis/src-tauri/icons/ios/AppIcon-76x76@2x.png': '26f89b9ef9b6cfec17b510ae305c0b45fb5d55139e46dc5f2d9ad68a27100357',
 'jarvis/src-tauri/icons/ios/AppIcon-83.5x83.5@2x.png': '57c90f3dd71d88aeaf4a44a9a5827f537859d3430705e5bc390b384db0a270e0',
 'jarvis/src-tauri/icons/jarvis-icon.svg': '329d076782d8451add90dd50e678dec52d1cad87eeaa5102f369bd89565ca47a'}
PRIVATE_PATH = re.compile(r'(^|/)(runtime-data|private|screenshots|\.env|auth\.json|credentials?|mcp-tokens)(/|$)|PROMPT_09|GOAL_09|\.(sqlite3?|db|png|jpe?g|pdf|xlsx|docx)$', re.I)
CREDENTIAL_FIELD = re.compile(r'(?i)["\']?(?:access_token|refresh_token|client_secret|api_key)["\']?\s*[:=]\s*["\'][A-Za-z0-9_./+\-=]{20,}["\']')

def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True).stdout

def inspect(name, content, mode='100644'):
    if mode not in {'100644','100755'}: return 'non-regular candidate'
    if name in REVIEWED_ASSETS and hashlib.sha256(content).hexdigest() == REVIEWED_ASSETS[name]: return None
    if PRIVATE_PATH.search(name): return 'private/artifact candidate'
    if len(content)>MAX_BYTES: return 'candidate exceeds reviewed size limit'
    if b'\0' in content: return 'binary candidate requires separate review'
    text=content.decode('utf-8', errors='strict')
    if any(p.search(text) for p in SECRET_PATTERNS) or CREDENTIAL_FIELD.search(text): return 'credential-shaped content'
    return None

def scan_commits(root, refs):
    findings=[]; seen=set()
    for ref in refs:
        for row in git(root,'ls-tree','-r','-z',ref).split(b'\0'):
            if not row: continue
            metadata,raw_name=row.split(b'\t',1); mode,kind,oid=metadata.decode().split(); name=raw_name.decode()
            if (name,oid) in seen: continue
            seen.add((name,oid))
            size=int(git(root,'cat-file','-s',oid))
            reason='candidate exceeds reviewed size limit' if size>MAX_BYTES else inspect(name,git(root,'cat-file','blob',oid),mode)
            if reason: findings.append((name,reason))
    return findings

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--commit',action='append',default=[]); args=parser.parse_args()
    try:
        if args.commit: findings=scan_commits(ROOT,args.commit)
        else:
            findings=[]
            for name in git(ROOT,'ls-files','--cached','--others','--exclude-standard','-z').split(b'\0'):
                if not name: continue
                relative=name.decode(); p=ROOT/relative
                if not p.exists(): continue
                reason=inspect(relative,p.read_bytes(),'120000' if p.is_symlink() else '100644')
                if reason: findings.append((relative,reason))
        for name,reason in findings: print(f'{name}: {reason}')
        if findings: return 1
        print('Candidate scan passed (credential patterns and private-path/content gates).'); return 0
    except (ValueError,UnicodeError,OSError,subprocess.CalledProcessError) as exc:
        print(f'Candidate scan could not complete: {type(exc).__name__}',file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
