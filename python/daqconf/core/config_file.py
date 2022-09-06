import json
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
import configparser

console = Console()
# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
import moo.oschema

moo.otypes.load_types('daqconf/confgen.jsonnet')
import dunedaq.daqconf.confgen as confgen

def default_config():
    console.log("Creating default daqconf configuration")
    output_dict = {}

    output_dict["daqconf"] = confgen.daqconf()
    output_dict["timing"] = confgen.timing()
    output_dict["hsi"] = confgen.hsi()
    output_dict["readout"] = confgen.readout()
    # Have to explicitly instantiate the object-type members
    trigger_conf = confgen.trigger()
    trigger_conf.trigger_activity_config = confgen.trigger_algo_config()
    trigger_conf.trigger_candidate_config = confgen.trigger_algo_config()
    output_dict["trigger"] = trigger_conf
    output_dict["dataflow"] = confgen.dataflow()
    output_dict["dqm"] = confgen.dqm()

    return output_dict

def parse_json(input_dict, filename):
    console.log(f"Parsing config json file {filename}")
    with open(filename, 'r') as f:
        json_obj = json.load(f)
    for k,v in json_obj.items():
        console.log(f"Updating config section {k} with {v}")
        if k in input_dict.keys():
            input_dict[k].update(v)
        if "dataflow." in k:
            appsection_found = False
            for app in input_dict["dataflow"].apps:
                if app["app_name"] == k[9:]:
                    appsection_found = True
                    input_dict["dataflow"].apps[app].update(v)
            if not appsection_found:
                newapp = confgen.dataflowapp().pod()
                newapp.update(v)
                newapp["app_name"] = k[9:]
                input_dict["dataflow"].apps += [newapp]

    return input_dict

def parse_ini(input_dict, filename):
    console.log(f"Parsing config ini file {filename}")

    config = configparser.ConfigParser()
    config.read(filename)
    for section in config.sections():
        sectiondict = {k:v for k,v in config[section].items()}
        for k,v in sectiondict.items():
            if v == "true" or v == "True":
                sectiondict[k] = True
            if v == "false" or v == "False":
                sectiondict[k] = False
        console.log(f"Updating config section {section} with {sectiondict}")
        if section in input_dict.keys():
            input_dict[section].update(sectiondict)
        if "dataflow." in section:
            appsection_found = False
            for app in input_dict["dataflow"].apps:
                if app["app_name"] == section[9:]:
                    appsection_found = True
                    input_dict["dataflow"].apps[app].update(sectiondict)
            if not appsection_found:
                newapp = confgen.dataflowapp().pod()
                newapp.update(sectiondict)
                newapp["app_name"] = section[9:]
                input_dict["dataflow"].apps += [newapp]

    return input_dict

            
