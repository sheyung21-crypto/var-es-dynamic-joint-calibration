"""Portable orchestration around the archived research routines; no model redesign."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'outputs/reference'
OUT = ROOT / 'outputs/reproduced'

def execute(relative_script, *args, env=None):
    command = [sys.executable, '-I', '-B', '-X', 'utf8', str(ROOT / relative_script), *map(str,args)]
    logs=ROOT/'outputs/verification/logs'; logs.mkdir(parents=True,exist_ok=True)
    log=logs/(Path(relative_script).stem+'_'+str(time.time_ns())+'.log')
    print('Running', relative_script, flush=True)
    start=time.time()
    with log.open('w',encoding='utf-8') as handle:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT)
    print(f'Exit {result.returncode}; {time.time()-start:.1f}s; {log.relative_to(ROOT)}',flush=True)
    if result.returncode:
        print(log.read_text(encoding='utf-8')[-6000:])
        raise SystemExit(result.returncode)

def review():
    """Regenerate presentation and inference from immutable archived outputs."""
    for source,dest in [('study2_run1','study2_run1'),('derived','derived')]:
        target=OUT/dest
        if not target.exists(): shutil.copytree(REF/source,target)
    if not (OUT/'study2_summary').exists():
        execute('code/pipeline/study2.py','summarize')
    execute('code/validation/verify_study2.py')
    execute('code/reporting/build_tables_figures.py')
    execute('code/reporting/paper_figures.py')
    execute('code/reporting/export_paper_tables.py')
    execute('code/validation/verify_paper_claims.py')
    execute('code/validation/compare_results.py')
    origin='replayed' if (OUT/'study1/confirm_meta.json').exists() else 'archived'
    print(f'Review path complete. Study 1 tables use {origin} estimates; consult verification status.',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','inputs','review','study1','study2','audit-study1','compare','leakage'])
    p.add_argument('--study1-data',type=Path,default=ROOT/'data/study1/raw')
    p.add_argument('--destination',type=Path)
    args=p.parse_args()
    (ROOT/'outputs/verification').mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    if args.stage=='prepare':
        if args.destination is None: p.error('prepare requires --destination PATH')
        target=args.destination.resolve()
        target.mkdir(parents=True,exist_ok=False)
        for name in ['code','data','provenance']:
            shutil.copytree(ROOT/name,target/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(REF,target/'outputs/reference')
        shutil.copyfile(ROOT/'requirements.txt',target/'requirements.txt')
        print('Fresh workspace:',target)
    elif args.stage=='inputs':
        extra=['--study1',args.study1_data.resolve()] if args.study1_data.exists() else []
        execute('code/data/manage_inputs.py','verify',*extra)
    elif args.stage=='study1':
        manifest=args.study1_data.resolve()/'fetch_manifest.json'
        expected=ROOT/'data/study1/expected_fetch_manifest.json'
        if not manifest.is_file():
            p.error('Study 1 requires fetch_manifest.json before fitting. First use code/data/manage_inputs.py import-study1 PATH to import the seven verified inputs and create the required manifest.')
        try:
            manifest_matches=json.loads(manifest.read_text(encoding='utf-8'))==json.loads(expected.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            manifest_matches=False
        if not manifest_matches:
            p.error('Study 1 acquisition manifest does not match the frozen manifest; no fitting was started.')
        execute('code/data/manage_inputs.py','verify','--study1',args.study1_data.resolve())
        execute('code/core/confirm/confirm_run.py',args.study1_data.resolve(),OUT/'study1')
    elif args.stage=='study2':
        execute('code/data/manage_inputs.py','verify')
        execute('code/pipeline/study2.py','forecast')
        execute('code/pipeline/study2.py','summarize')
        execute('code/validation/verify_study2.py')
    elif args.stage=='audit-study1':
        env=os.environ.copy(); env['VAR_STUDY1_DATA']=str(args.study1_data.resolve())
        execute('code/validation/audit_study1.py',env=env)
    elif args.stage=='review': review()
    elif args.stage=='compare': execute('code/validation/compare_results.py')
    elif args.stage=='leakage': execute('code/validation/leakage_checks.py')

if __name__=='__main__': main()
