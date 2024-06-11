import conffwk
import confmodel

import os
import glob


def enable(oksfile, disable, resource, session_name):
    """Script to enable or disable (-d) Resources from the first Session of the
    specified OKS database file"""
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
    disabled = session.disabled
    for res in resource:
        try:
            res_dal = db.get_dal("ResourceBase", res)
        except:
            print(f"Error could not find Resource {res} in file {oksfile}")
            continue

        if disable:
            if res_dal in disabled:
                print(
                    f"{res} is already in disabled relationship of Session {session.id}"
                )
            else:
                # Add to the Segment's disabled list
                print(f"Adding {res} to disabled relationship of Session {session.id}")
                disabled.append(res_dal)
        else:
            if res_dal not in disabled:
                print(f"{res} is not in disabled relationship of Session {session.id}")
            else:
                # Remove from the Segments disabled list
                print(
                    f"Removing {res} from disabled relationship of Session {session.id}"
                )
                disabled.remove(res_dal)
    session.disabled = disabled
    db.update_dal(session)
    db.commit()
