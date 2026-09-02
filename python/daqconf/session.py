import conffwk

def get_segment_apps(segment: object) -> list[object]:
    """
    Gather the list of applications in the segment and its sub-segments
    """
    apps = []

    for ss in segment.segments:
        apps += get_segment_apps(ss)

    for aa in segment.applications:
        apps.append(aa)
    
    apps.append(segment.controller)

    return apps


def get_session_apps(confdb: conffwk.Configuration, session_name: str = "") -> list[object] | None:
    """
    Gather the apps defined used in a session.
    """
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


def get_apps_in_any_session(confdb: conffwk.Configuration) -> dict[str, list[object]]:
    """
    Gather the applications used in any session present in the database
    """

    output = {}
    session_dals = confdb.get_dals(class_name="Session")
    if len(session_dals) == 0:
        print(f"Error could not find any Session in file {confdb.databases}")
        return {}

    for session in session_dals:
        segment = session.segment
        output[session.id] = get_segment_apps(segment)

    return output


def include_excludable_entity_in_session(
    db: conffwk.Configuration,
    session_name: str,
    excludable_entity: list[str],
    exclude: bool,
) -> None:
    """Script to include or exclude (-d, for the old term disabled) ExcludableEntitys from
    the first Session of the specified OKS database file"""
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
        
    excluded = session.excluded
    for res in excludable_entity:
        try:
            res_dal = db.get_dal("ExcludableEntity", res)
        except:
            print(f"Error could not find ExcludableEntity {res} in file {db.databases}")
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

