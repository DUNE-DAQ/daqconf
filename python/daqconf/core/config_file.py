import os
import math
import sys
import glob
import rich.traceback
from rich.console import Console
from collections import defaultdict
from os.path import exists, join
import random
import string

console = Console()
# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()


# Load configuration types
import moo.otypes
import moo.oschema

def _strict_recursive_update(dico1, dico2):
    for k, v in dico2.items():
        if isinstance(v, dict):
            if v != {}:
                try:
                    dico1[k] = _strict_recursive_update(dico1.get(k, {}), v)
                except Exception as e:
                    raise RuntimeError(f'Couldn\'t update the dictionary of keys: {list(dico1.keys())} with dictionary \'{k}\'\nError: {e}')
            else:
                continue
        else:
            if not k in dico1:
                raise RuntimeError(f'\'{k}\' key is unknown, available keys are: {list(dico1.keys())}')
            dico1[k] = v
    return dico1

def parse_json(filename, schemed_object):
    console.log(f"Parsing config json file {filename}")

    with open(filename, 'r') as f:
        try:
            import json
            try:
                new_parameters = json.load(f)
                # Validate the heck out of this but that doesn't change the object itself (ARG)
                _strict_recursive_update(schemed_object.pod(), new_parameters)
                # now its validated, update the object with moo
                schemed_object.update(new_parameters)
            except Exception as e:
                raise RuntimeError(f'Couldn\'t update the object {schemed_object} with the file {filename},\nError: {e}')
        except Exception as e:
            raise RuntimeError(f"Couldn't parse {filename}, error: {str(e)}")
        return schemed_object

    raise RuntimeError(f"Couldn't find file {filename}")


def _recursive_section(sections, data):
    if len(sections) == 1:
        d = data
        for k,v in d.items():
            if v == "true" or v == "True":
                d[k] = True
            if v == "false" or v == "False":
                d[k] = False
        return {sections[0]: d}
    else:
        return {sections[0]: _recursive_section(sections[1:], data)}

def parse_ini(filename, schemed_object):
    console.log(f"Parsing config ini file {filename}")

    import configparser
    config = configparser.ConfigParser()
    try:
        config.read(filename)
    except Exception as e:
        raise RuntimeError(f"Couldn't parse {filename}, error: {str(e)}")

    config_dict = {}

    for sect in config.sections():
        sections = sect.split('.')
        data = {k:v for k,v in config.items(sect)}
        if sections[0] in config_dict:
            config_dict[sections[0]].update(_recursive_section(sections, data)[sections[0]])
        else:
            config_dict[sections[0]] = _recursive_section(sections, data)[sections[0]]

    try:
        new_parameters = config_dict
        # validate the heck out of this but that doesn't change the object itself (ARG)
        _strict_recursive_update(schemed_object.pod(), new_parameters)
        # now its validated, update the object with moo
        schemed_object.update(new_parameters)
        return schemed_object
    except Exception as e:
        raise RuntimeError(f'Couldn\'t update the object {schemed_object} with the file {filename},\nError: {e}')
