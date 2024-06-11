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


def get_session_apps(oksfile, session_name=""):
    """Get the apps defined in the given session"""
    session_db = conffwk.Configuration("oksconflibs:" + oksfile)
    if session_name == "":
        session_dals = session_db.get_dals(class_name="Session")
        if len(session_dals) == 0:
            print(f"Error could not find any Session in file {oksfile}")
            return
        session = session_dals[0]
    else:
        try:
            session = session_db.get_dal("Session", session_name)
        except:
            print(f"Error could not find Session {session_name} in file {oksfile}")
            return

    segment = session.segment

    return get_segment_apps(segment)


def get_database_apps(oksfile):

    output = {}
    session_db = conffwk.Configuration("oksconflibs:" + oksfile)
    session_dals = session_db.get_dals(class_name="Session")
    if len(session_dals) == 0:
        print(f"Error could not find any Session in file {oksfile}")
        return {}

    for session in session_dals:
        segment = session.segment
        output[session.id] = get_segment_apps(segment)

    return output