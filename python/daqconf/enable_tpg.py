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

def enable_tpg(oksfile, disable, session_name):
    """Script to enable or disable (-d) TP generation in ReadoutApplications of the
    specified OKS configuration"""
    db = conffwk.Configuration("oksconflibs:" + oksfile)
    if session_name == "":
        session_dals = db.get_dals(class_name="Session")
        if len(session_dals) == 0:
            print(f"Error could not find any Session in file {oksfile}")
            return
        session = session_dals[0]
    else:
        try:
            session = db.get_dal("Session", session_name)
        except:
            print(f"Error could not find Session {session_name} in file {oksfile}")
            return
    # disabled = session.disabled
    segment = session.segment
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
