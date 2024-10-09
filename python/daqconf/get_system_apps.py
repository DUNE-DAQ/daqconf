import conffwk
import confmodel

import os
import glob


def get_segment_apps(segment):
    apps = []

    for ss in segment.segments:
        apps += get_segment_apps(ss)

    for aa in segment.applications:
        apps.append(aa.id)

    return apps


def get_system_apps(oksfile, system_name=""):
    """Get the apps defined in the given system"""
    system_db = conffwk.Configuration("oksconflibs:" + oksfile)
    if system_name == "":
        system_dals = system_db.get_dals(class_name="System")
        if len(system_dals) == 0:
            print(f"Error could not find any System in file {oksfile}")
            return
        system = system_dals[0]
    else:
        try:
            system = system_db.get_dal("System", system_name)
        except:
            print(f"Error could not find System {system_name} in file {oksfile}")
            return

    segment = system.segment

    return get_segment_apps(segment)


def get_database_apps(oksfile):

    output = {}
    system_db = conffwk.Configuration("oksconflibs:" + oksfile)
    system_dals = system_db.get_dals(class_name="System")
    if len(system_dals) == 0:
        print(f"Error could not find any System in file {oksfile}")
        return {}

    for system in system_dals:
        segment = system.segment
        output[system.id] = get_segment_apps(segment)

    return output