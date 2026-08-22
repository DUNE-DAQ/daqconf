import conffwk
import confmodel_dal

import os
import glob


def include(oksfile: str, exclude: bool, excludable_entity: list[str], session_name: str) -> None:
    """Script to include or exclude (-d, for the old term disabled) ExcludableEntitys from the 
first Session of the specified OKS database file"""
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
    excluded = session.excluded
    for res in excludable_entity:
        try:
            res_dal = db.get_dal("ExcludableEntity", res)
        except:
            print(f"Error could not find ExcludableEntity {res} in file {oksfile}")
            continue

        if exclude:
            if res_dal in excluded:
                print(
                    f"{res} is already in excluded relationship of Session {session.id}"
                )
            else:
                # Add to the Segment's excluded list
                print(f"Adding {res} to excluded relationship of Session {session.id}")
                excluded.append(res_dal)
        else:
            if res_dal not in excluded:
                print(f"{res} is not in excluded relationship of Session {session.id}")
            else:
                # Remove from the Segments excluded list
                print(
                    f"Removing {res} from excluded relationship of Session {session.id}"
                )
                excluded.remove(res_dal)
    session.excluded = excluded
    db.update_dal(session)
    db.commit()
