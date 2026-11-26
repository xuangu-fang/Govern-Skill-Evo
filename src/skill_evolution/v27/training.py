"""Independent immutable SkillAdam membership view over the downloaded content."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from skilladam.benchmarks.lmb.choices import normalize_choices, shuffle_choices
from .facts import require
from .benchmarks.lmb import protocol as p

MERGED_POOL='v27_lmb_skilladam53_v1'
RESOURCES=Path(__file__).with_name('resources')
POOL_IDS=json.loads((RESOURCES/'lmb_ids.json').read_text())

@dataclass(frozen=True)
class Case:
    case_id: str
    payload: dict
    reference: dict
    metadata: dict

class OptimizationDataset:
    optimization_pool=MERGED_POOL
    def __init__(self, prepared_root):
        self.root=Path(prepared_root).resolve()
        manifest=json.loads((self.root/'split_manifest.json').read_text())
        require(manifest['content_revision']==p.CONTENT_REVISION,'Unexpected content revision')
        require(manifest == json.loads((RESOURCES/'lmb_content_manifest.json').read_text()), 'Content manifest differs from frozen source')
        for rel, checksum in manifest['output_sha256'].items():
            require(p.file_digest(self.root/rel) == checksum, 'Prepared source bytes changed')
        raw = self.root.parent/'raw'
        for rel, info in manifest['source_files'].items():
            require(p.file_digest(raw/rel) == info['sha256'], 'Raw source bytes changed')
        originals={}
        for split in ('train','val','test'):
            for row in json.loads((self.root/split/'items.json').read_text()):
                require(row['id'] not in originals,'Duplicate dataset ID'); originals[row['id']]=row
        ids=[i for values in POOL_IDS.values() for i in values]
        require(len(ids)==len(set(ids))==177 and set(ids)==set(originals),'Fixed ID coverage differs')
        require([len(POOL_IDS[s]) for s in ('train','val','test')]==[35,18,124],'Invalid frozen split counts')
        self.source_splits={'train':sorted(POOL_IDS['train']),'validation':sorted(POOL_IDS['val']),
                            'test':list(POOL_IDS['test'])}
        self.splits={'train':self.source_splits['train']+self.source_splits['validation'],
                     'validation':[],'test':self.source_splits['test']}
        self.rows={}
        for source,values in self.source_splits.items():
            for uid in values:
                row=deepcopy(originals[uid]); choices=list(normalize_choices(sorted(row['choices'],key=lambda c:c['label'])))
                presented,correct=shuffle_choices(choices,row['correct_choice']['label'],seed=42,item_id=uid)
                # Obtain the permutation from unique temporary labels, independent of duplicate option text.
                markers=[{'label':c['label'],'text':c['label']} for c in choices]
                shuffled,_=shuffle_choices(markers,row['correct_choice']['label'],seed=42,item_id=uid)
                mapping={c['text']:c['label'] for c in shuffled}
                row.update(source_split=source,effective_split='test' if source=='test' else 'train',
                           content_revision=p.CONTENT_REVISION,content_sha256=p.digest(originals[uid]),
                           presented_choices=presented,presented_correct_label=correct,label_mapping=mapping)
                self.rows[uid]=row
        self.source_hashes={str(path.relative_to(self.root)):p.file_digest(path)
                            for path in sorted(self.root.rglob('*.json'))}
    def case(self,uid):
        row=self.rows[uid]
        return Case(uid,{'question':row['question'].strip(),'choices':deepcopy(row['presented_choices'])},
                    {'label':row['presented_correct_label']},
                    {'split':row['effective_split'],'source_split':row['source_split']})
    def cases(self,split): return tuple(self.case(uid) for uid in self.splits[split])
    def batches(self): return [self.splits['train'][i:i+10] for i in range(0,53,10)]
    def snapshot(self):
        fresh=type(self)(self.root)
        require(p.equal(fresh.rows,self.rows) and fresh.source_hashes==self.source_hashes,'Dataset changed after binding')
        return {'root':str(self.root),'content_revision':p.CONTENT_REVISION,'source_hashes':self.source_hashes,
                'profile_sha256':p.file_digest(RESOURCES/'lmb_ids.json'),
                'rows':{k:p.digest(v) for k,v in self.rows.items()},'source_splits':self.source_splits,'splits':self.splits}
    def export_view(self,directory):
        from .stages import freeze
        out=Path(directory).resolve()
        require(not out.is_relative_to(self.root) and not self.root.is_relative_to(out),'Separate data view required')
        freeze(out/'manifest.json',self.snapshot())
        freeze(out/'items.json',list(self.rows.values()))
        return out

def load_dataset(prepared_root,optimization_pool=MERGED_POOL):
    require(optimization_pool==MERGED_POOL,'Explicit LMB optimization pool required')
    return OptimizationDataset(prepared_root)
