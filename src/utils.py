import yaml
import logging
import pprint


def load_yml(file):
    yml = None
    with open(file, 'r') as yml:
        yml = yaml.load(yml, Loader=yaml.FullLoader)
    return yml


def print_yml(file):
    cfg = pprint.pformat(yml)
    logging.debug(cfg)

