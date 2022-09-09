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


def parse_json(filename, schemed_object):
    console.log(f"Parsing config json file {filename}")

    with open(filename, 'r') as f:
        try:
            import json
            schemed_object.update(json.load(f))
        except Exception as e:
            raise RuntimeError(f"Couldn't parse {filename}, error: {str(e)}")
        return schemed_object

    raise RuntimeError(f"Couldn't find file {filename}")


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
        config_dict[sect] = dict(config.items(sect))
    try:
        return schemed_object.update(config_dict)
    except Exception as e:
        raise RuntimeError(f"Couldn't parse {filename}, error: {str(e)}")
