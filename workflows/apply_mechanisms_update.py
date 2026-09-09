#!/usr/bin/env python3
"""Add this bundle to a CLEAN review branch without overwriting any existing file.

Never runs reset, restore, stash, commit, push, or deletes repository files.
Uses only the Python standard library. Run the top-level bundled APPLY_UPDATE.py.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

REPOSITORY='uskutsav-cpu/cdt-topology-dimred'
BASE_COMMIT='7086a739da6f3c0f56788e211c78424a0cf65c22'
ALLOWED_PREFIXES=('src/cdt_mechanisms/','tests/mechanisms/','configs/mechanisms/',
                  'results/mechanisms/','results/mechanisms_secondary/','results/mechanisms_validation/',
                  'docs/mechanisms/','environment/mechanisms-','workflows/')


def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path,*args: str,check: bool=True) -> str:
    completed=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,check=False)
    if check and completed.returncode:
        raise ValueError(f'git {args[0]} failed: {completed.stderr.strip()}')
    return completed.stdout.strip()


def canonical_origin(value: str) -> str:
    patterns=(r'https://github\.com/([^/]+/[^/]+?)(?:\.git)?/?',
              r'git@github\.com:([^/]+/[^/]+?)(?:\.git)?/?',
              r'ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?/?')
    for pattern in patterns:
        match=re.fullmatch(pattern,value)
        if match: return match.group(1)
    raise ValueError('origin is not an accepted github.com repository URL')


def safe_relative(value: str) -> PurePosixPath:
    if not isinstance(value,str) or not value or '\\' in value:
        raise ValueError('unsafe manifest path')
    path=PurePosixPath(value)
    if path.is_absolute() or str(path)!=value or any(part in ('..','.git') for part in path.parts):
        raise ValueError('unsafe manifest path')
    if not value.startswith(ALLOWED_PREFIXES): raise ValueError('path is outside the additive update scope')
    return path


def no_symlink_path(root: Path,relative: PurePosixPath) -> Path:
    result=root
    for part in relative.parts:
        result=result/part
        if result.is_symlink(): raise ValueError(f'symlink path refused: {result}')
    return result


def inspect_bundle(bundle: Path) -> tuple[dict,dict[str,Path]]:
    if bundle.is_symlink(): raise ValueError('bundle root is a symlink')
    manifest_path=bundle/'BUNDLE_MANIFEST.json'; payload=bundle/'payload'
    if manifest_path.is_symlink() or payload.is_symlink(): raise ValueError('symlink bundle metadata/payload')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='cdt-mechanisms-additive-bundle-v1': raise ValueError('unrecognized bundle')
    if manifest.get('repository')!=REPOSITORY or manifest.get('base_commit')!=BASE_COMMIT:
        raise ValueError('bundle provenance mismatch')
    files=manifest.get('files')
    if not isinstance(files,dict) or not files: raise ValueError('empty bundle')
    actual={p.relative_to(payload).as_posix() for p in payload.rglob('*') if p.is_file() or p.is_symlink()}
    if actual!=set(files): raise ValueError('payload file set differs from manifest')
    sources={}
    for rel,digest in files.items():
        path=no_symlink_path(payload,safe_relative(rel))
        if not isinstance(digest,str) or re.fullmatch('[a-f0-9]{64}',digest) is None:
            raise ValueError('invalid digest')
        if not path.is_file() or sha256(path)!=digest: raise ValueError(f'payload hash mismatch: {rel}')
        sources[rel]=path
    return manifest,sources


def preflight_repository(repo: Path) -> None:
    if not repo.is_dir(): raise ValueError('repository directory does not exist')
    if Path(git(repo,'rev-parse','--show-toplevel')).resolve()!=repo.resolve():
        raise ValueError('target must be the repository root')
    if canonical_origin(git(repo,'remote','get-url','origin'))!=REPOSITORY:
        raise ValueError(f'origin is not {REPOSITORY}')
    branch=git(repo,'branch','--show-current')
    if not branch or branch in ('main','master'): raise ValueError('use a named review branch, not main/master/detached HEAD')
    if git(repo,'status','--porcelain','--untracked-files=all'):
        raise ValueError('working tree is not clean; use a fresh clone, not a live simulation workspace')
    ancestor=subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',BASE_COMMIT,'HEAD'],capture_output=True)
    if ancestor.returncode: raise ValueError(f'HEAD is not descended from audited base {BASE_COMMIT}')


def plan_files(repo: Path,manifest: dict,sources: dict[str,Path]) -> tuple[list[str],list[str]]:
    added=[]; identical=[]
    for rel in sorted(sources):
        destination=no_symlink_path(repo,safe_relative(rel))
        if destination.exists():
            if not destination.is_file() or sha256(destination)!=manifest['files'][rel]:
                raise ValueError(f'existing file differs; no files changed: {rel}')
            identical.append(rel)
        else:
            for parent in destination.parents:
                if parent==repo: break
                if parent.exists() and not parent.is_dir(): raise ValueError(f'parent is not a directory: {parent}')
            added.append(rel)
    return added,identical


def install(bundle: Path,repo: Path,*,apply: bool=False) -> dict:
    bundle=bundle.absolute(); repo=repo.absolute()
    manifest,sources=inspect_bundle(bundle); preflight_repository(repo)
    added,identical=plan_files(repo,manifest,sources)
    if apply:
        # All conflicts are checked first. Exclusive writes also reject a racing writer.
        # An I/O interruption can leave a partial ADDITIVE install, never overwritten files.
        for rel in added:
            source=sources[rel]
            if sha256(source)!=manifest['files'][rel]: raise ValueError(f'payload changed after preflight: {rel}')
            destination=no_symlink_path(repo,safe_relative(rel))
            destination.parent.mkdir(parents=True,exist_ok=True)
            no_symlink_path(repo,safe_relative(rel))
            with destination.open('xb') as output,source.open('rb') as input_file:
                for chunk in iter(lambda:input_file.read(1024*1024),b''): output.write(chunk)
                output.flush(); os.fsync(output.fileno())
            if sha256(destination)!=manifest['files'][rel]: raise ValueError(f'post-copy hash mismatch: {rel}')
    return dict(applied=apply,new_files=len(added),identical_files=len(identical),
                overwritten_files=0,committed=False,pushed=False,files=added)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    parser.add_argument('--bundle',type=Path,default=Path(__file__).absolute().parent)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--apply',action='store_true')
    mode.add_argument('--dry-run',action='store_true',help='default: inspect only')
    args=parser.parse_args()
    try: print(json.dumps(install(args.bundle,args.repository,apply=args.apply),indent=2)); return 0
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
