"""Offline facts-only reaggregation of a completed pair Attribution; no Memory commit."""
import argparse
from pathlib import Path
import sys
import shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from src.skill_evolution import attribution_pairs_v19 as pairs
    from src.skill_evolution.evolution_replay_v19 import _load,_save,_file_digest
    from src.skill_evolution.memory_store_v19 import require
    from src.skill_evolution.edit_tracking_v19 import encode,digest
    source,output=args.source.resolve(),args.output.resolve()
    require(not output.exists() and source not in output.parents,'new independent output required')
    data=_load(source/'input.json')
    old=pairs.load_complete(source,data)
    new=pairs.aggregate(data,old.payload['pair_results'])
    shutil.copytree(source,output)
    _save(output/'attributions.json',new.payload)
    marker=_load(output/'validation.json')
    marker['files']={n:_file_digest(output/n) for n in pairs.FILES}
    _save(output/'validation.json',marker)
    _save(output/'semantics-migration.json',{
        'schema_version':'attribution_semantics_migration_v19.1',
        'source':str(source),'old_batch_sha256':digest(old.payload_json),
        'new_batch_sha256':digest(new.payload_json),'pair_responses_reused':len(old.payload['pair_results']),
        'implementation_sha256':_file_digest(ROOT/'src/skill_evolution/attribution_semantics_v19.py'),
        'memory_committed':False})
    require(pairs.load_complete(output,data)==new,'new aggregate verification failed')
    print(encode({'status':'COMPLETE','output':str(output),'memory_committed':False}))


if __name__=='__main__':main()
