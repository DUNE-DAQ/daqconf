import conffwk
import confmodel
import appmodel

import os
import glob

def get_segment_apps(segment):
    apps = []

    for ss in segment.segments:
        apps += get_segment_apps(ss)

    for aa in segment.applications:
        apps.append(aa.id)

    return apps

def enable_tpg(oksfile, disable, system_name):
    """Script to enable or disable (-d) TP generation in ReadoutApplications of the
    specified OKS configuration"""
    db = conffwk.Configuration("oksconflibs:" + oksfile)
    if system_name == "":
        system_dals = db.get_dals(class_name="System")
        if len(system_dals) == 0:
            print(f"Error could not find any System in file {oksfile}")
            return
        system = system_dals[0]
    else:
        try:
            system = db.get_dal("System", system_name)
        except:
            print(f"Error could not find System {system_name} in file {oksfile}")
            return
    # disabled = system.disabled
    segment = system.segment
    apps = get_segment_apps(segment)
    for aa in apps:
        try:
            roapp = db.get_dal(class_name="ReadoutApplication", uid=aa)
            if disable:
                roapp.tp_generation_enabled = 0
                roapp.ta_generation_enabled = 0
                print(f"Disable TP generation in {roapp.id}.")
            else:
                roapp.tp_generation_enabled = 1
                roapp.ta_generation_enabled = 1
                print(f"Enable TP generation in {roapp.id}.")
            db.update_dal(roapp)
        except:
            continue
            
    db.commit()
