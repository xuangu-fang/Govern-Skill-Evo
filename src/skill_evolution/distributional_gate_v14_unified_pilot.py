"""v14 task-stratified bootstrap adapted only to Unified pilot workload."""
import random
from collections import defaultdict
from src.skill_evolution.distributional_gate_v14 import is_epsilon_pareto_positive,gate_decision

def evaluate_unified_gate(pairs):
 if len(pairs)!=102:raise ValueError('Expected 102 matched pairs')
 clusters=defaultdict(list)
 for p in pairs:clusters[p['domain'],p['task_id']].append(p)
 if len(clusters)!=34 or any(len(v)!=3 or sorted(x['rollout_index'] for x in v)!=[1,2,3] for v in clusters.values()):raise ValueError('Invalid task clusters')
 strata={d:[] for d in ['airline','retail']}
 for (d,t),rs in sorted(clusters.items()):
  if len({x['seed'] for x in rs})!=3:raise ValueError('Duplicate seeds')
  strata[d].append((sum(x['candidate_success']-x['parent_success'] for x in rs),sum(x['candidate_compliance']-x['parent_compliance'] for x in rs)))
 if {d:len(v) for d,v in strata.items()}!={'airline':20,'retail':14}:raise ValueError('Invalid domain composition')
 rng=random.Random(200);positive=0
 for _ in range(10000):
  ds=dc=0
  for domain in sorted(strata):
   vals=strata[domain]
   for _ in range(len(vals)):
    a,b=rng.choice(vals);ds+=a;dc+=b
  positive+=is_epsilon_pareto_positive(ds,dc,1)
 ds=sum(a for v in strata.values() for a,b in v);dc=sum(b for v in strata.values() for a,b in v)
 return {'matched_pairs':102,'task_clusters':34,'domain_clusters':{'airline':20,'retail':14},'bootstrap_replicates':10000,'bootstrap_seed':200,'bootstrap_unit':'task','rollouts_per_cluster':3,'stratified_by_domain':True,'epsilon_pair_count':1,'epsilon_rate':1/102,'delta_success_count':ds,'delta_compliance_count':dc,'delta_success_rate':ds/102,'delta_compliance_rate':dc/102,'positive_count':positive,'P':positive/10000,'threshold':0.80,'decision':gate_decision(positive/10000,0.80)}
