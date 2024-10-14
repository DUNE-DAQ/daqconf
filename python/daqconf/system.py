import conffwk

def get_segment_apps(segment):
    apps = []

    for ss in segment.segments:
        apps += get_segment_apps(ss)

    for aa in segment.applications:
        apps.append(aa)
    
    apps.append(segment.controller)

    return apps


def get_system_apps(confdb, system_name=""):
    """Get the apps defined in the given system"""
    if system_name == "":
        system_dals = confdb.get_dals(class_name="System")
        if len(system_dals) == 0:
            print(f"Error could not find any System in file {confdb.databases}")
            return
        system = system_dals[0]
    else:
        try:
            system = confdb.get_dal("System", system_name)
        except:
            print(f"Error could not find System {system_name} in file {confdb.databases}")
            return

    segment = system.segment

    return get_segment_apps(segment)


def get_apps_in_any_system(confdb):

    output = {}
    system_dals = confdb.get_dals(class_name="System")
    if len(system_dals) == 0:
        print(f"Error could not find any System in file {confdb.databases}")
        return {}

    for system in system_dals:
        segment = system.segment
        output[system.id] = get_segment_apps(segment)

    return output


def enable_resource_in_system(db, system_name: str, resource: list[str], disable: bool):
    """Script to enable or disable (-d) Resources from the first System of the
    specified OKS database file"""
    if system_name == "":
        system_dals = db.get_dals(class_name="System")
        if len(system_dals) == 0:
            print(f"Error could not find any System in file {db.databases}")
            return
        system = system_dals[0]
    else:
        try:
            system = db.get_dal("System", system_name)
        except:
            print(f"Error could not find System {system_name} in file {db.databases}")
            return
        
    disabled = system.disabled
    for res in resource:
        try:
            res_dal = db.get_dal("ResourceBase", res)
        except:
            print(f"Error could not find Resource {res} in file {db.databases}")
            continue

        if disable:
            if res_dal in disabled:
                print(
                    f"{res} is already in disabled relationship of System {system.id}"
                )
            else:
                # Add to the Segment's disabled list
                print(f"Adding {res} to disabled relationship of System {system.id}")
                disabled.append(res_dal)
        else:
            if res_dal not in disabled:
                print(f"{res} is not in disabled relationship of System {system.id}")
            else:
                # Remove from the Segments disabled list
                print(
                    f"Removing {res} from disabled relationship of System {system.id}"
                )
                disabled.remove(res_dal)
    system.disabled = disabled
    db.update_dal(system)
    db.commit()

