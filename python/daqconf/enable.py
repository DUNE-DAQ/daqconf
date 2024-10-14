import conffwk
import confmodel

import os
import glob


def enable(oksfile, disable, resource, system_name):
    """Script to enable or disable (-d) Resources from the first System of the
    specified OKS database file"""
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
    disabled = system.disabled
    for res in resource:
        try:
            res_dal = db.get_dal("ResourceBase", res)
        except:
            print(f"Error could not find Resource {res} in file {oksfile}")
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
