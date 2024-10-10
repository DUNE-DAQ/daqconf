import conffwk

def get_segment_apps(segment):
    apps = []

    for ss in segment.segments:
        apps += get_segment_apps(ss)

    for aa in segment.applications:
        apps.append(aa)
    
    apps.append(segment.controller)

    return apps


def get_session_apps(confdb, session_name=""):
    """Get the apps defined in the given session"""
    if session_name == "":
        session_dals = confdb.get_dals(class_name="Session")
        if len(session_dals) == 0:
            print(f"Error could not find any Session in file {confdb.databases}")
            return
        session = session_dals[0]
    else:
        try:
            session = confdb.get_dal("Session", session_name)
        except:
            print(f"Error could not find Session {session_name} in file {confdb.databases}")
            return

    segment = session.segment

    return get_segment_apps(segment)


def get_apps_in_any_session(confdb):

    output = {}
    session_dals = confdb.get_dals(class_name="Session")
    if len(session_dals) == 0:
        print(f"Error could not find any Session in file {confdb.databases}")
        return {}

    for session in session_dals:
        segment = session.segment
        output[session.id] = get_segment_apps(segment)

    return output


def enable_resource_in_session(db, session_name: str, resource: list[str], disable: bool):
    """Script to enable or disable (-d) Resources from the first Session of the
    specified OKS database file"""
    if session_name == "":
        session_dals = db.get_dals(class_name="Session")
        if len(session_dals) == 0:
            print(f"Error could not find any Session in file {db.databases}")
            return
        session = session_dals[0]
    else:
        try:
            session = db.get_dal("Session", session_name)
        except:
            print(f"Error could not find Session {session_name} in file {db.databases}")
            return
        
    disabled = session.disabled
    for res in resource:
        try:
            res_dal = db.get_dal("ResourceBase", res)
        except:
            print(f"Error could not find Resource {res} in file {db.databases}")
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

