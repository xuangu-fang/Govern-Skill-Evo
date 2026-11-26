"""Explicit campaign variants; v28.1 reuses the v28 execution chain."""
from pathlib import Path

V28 = 'v28_campaign_v1'
V28_1 = 'v28_1_campaign_v1'
SUPPORTED = (V28, V28_1)
REVIEWED = Path(__file__).resolve().parents[3] / 'docs/methods/v28_1'


def check(profile):
    if profile not in SUPPORTED:
        raise ValueError('Unsupported SearchQA method profile')
    return profile


def prompt_versions(profile):
    check(profile)
    versions = {name: f'v28_searchqa_{name}_v1'
                for name in ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay')}
    versions['replay'] = 'v28_searchqa_replay_v3'
    if profile == V28_1:
        versions.update(diagnosis='v28_1_searchqa_diagnosis_v1',
                        preconditioner='v28_1_searchqa_preconditioner_v1')
    return versions
