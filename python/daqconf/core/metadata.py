import json
import os
import sys
from rich.console import Console
from os.path import exists, join

console = Console()

def write_metadata_file(json_dir, generator):
    console.log("Generating metadata file")
    with open(join(json_dir, f"{generator}.info"), 'w') as f:
        daqconf_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))

        buildinfo_file=join(daqconf_dir, "daqconf_build_info.json")
        buildinfo = {}
        #console.log(f"Buildinfo file is {buildinfo_file}")
        if exists(buildinfo_file):
            with open(buildinfo_file, 'r') as ff:
                try:
                    #console.log(f"Reading buildinfo file {buildinfo_file}")
                    buildinfo = json.load(ff)
                except json.decoder.JSONDecodeError as e:
                    console.log(f"Error reading buildinfo file {buildinfo_file}: {e}")

        daqconf_info = {
            "command_line": ' '.join(sys.argv),
            "daqconf_dir": daqconf_dir,
            "build_info": buildinfo
        }
        json.dump(daqconf_info, f, indent=4, sort_keys=True)