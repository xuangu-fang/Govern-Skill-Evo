"""Configuration changes for the official optimizer profile."""
from copy import deepcopy

from .layout import output_binding


def desired_config(source, experiment):
    cfg = deepcopy(source)
    cfg['optimizer_transport'].update(model='deepseek-flash',
        base_url='https://api.deepseek.com', api_key_env='ALFWORLD_OPTIMIZER_KEY')
    cfg['output_root'] = output_binding(experiment)
    return cfg


def desired_actor(source):
    return deepcopy(source)
