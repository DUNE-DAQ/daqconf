import conffwk
import confmodel_dal
import appmodel_dal

import os
import glob

def get_segment_apps(segment: object) -> list[str]:
    apps = []

    for ss in segment.segments:
        apps += get_segment_apps(ss)

    for aa in segment.applications:
        apps.append(aa.id)

    return apps

def include_tpg(oksfile: str, exclude: bool, session_name: str) -> None:
    """Script to include or exclude (-d, for the old term disable) TP generation in 
ReadoutApplications of the specified OKS configuration"""
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
    # excluded = session.excluded
    segment = session.segment
    apps = get_segment_apps(segment)
    for aa in apps:
        try:
            roapp = db.get_dal(class_name="ReadoutApplication", uid=aa)
            if exclude:
                roapp.tp_generation_included = 0
                roapp.ta_generation_included = 0
                print(f"Exclude TP generation in {roapp.id}.")
            else:
                roapp.tp_generation_included = 1
                roapp.ta_generation_included = 1
                print(f"Include TP generation in {roapp.id}.")
            db.update_dal(roapp)
        except:
            continue
            
    db.commit()
