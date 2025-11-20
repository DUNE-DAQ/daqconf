from pathlib import Path
import conffwk
import sys
import os
from logging import getLogger
from typing import Optional, Tuple
log = getLogger('daqconf.consolidate')


def get_all_includes(db, file):
    includes = db.get_includes(file)
    for include in includes:
        if "data.xml" not in include:
            continue
        includes += get_all_includes(db, include)

    return list(set(includes))

def consolidate_db(oksfile: str, output_file: str, session_id: Optional[str] = None)->None:
    """Consolidates a single session

    :param oksfile: OKS file(s) to consolidate
    :param output_file: File to output consolidated database to 
    :param session_id: Name of session, defaults to None
    """    
    log.info(f"Consolidating database into output database '{output_file}'. Input database: '{oksfile}'.")

    sys.setrecursionlimit(10000)  # for example
    db, new_db = create_copy_template(oksfile, output_file)

    if session_id is None:
        log.debug("Consolidating all dals in %s into %s", oksfile, output_file)
        consolidate_full(db, new_db)
    else:
        log.debug("Consolidating all dals in session %s from %s into %s", session_id, oksfile, output_file)

        consolidate_session(db, new_db, session_id)


def create_copy_template(oksfile: str, output_file: str)->Tuple[conffwk.Configuration, conffwk.Configuration]:
    '''
    Creates a blank oks .data.xml file stored in output_file with all the schema includes of oksfile
    :param oksfile: OKS file to copy includes from
    :param output_file: OKS file to copy includes into

    :returns: Tuple of old_db, copied_db
    '''
    log.debug("Reading database")
    db = conffwk.Configuration("oksconflibs:" + oksfile)

    schemafiles = []
    includes = get_all_includes(db, None)
    schemafiles += [i for i in includes if "schema.xml" in i]
    log.debug(f"Included schemas: {schemafiles}")

    log.debug("Creating new database")
    new_db = conffwk.Configuration("oksconflibs")
    new_db.create_db(output_file, schemafiles)
    new_db.commit()
    
    return db, new_db


def consolidate_full(db: conffwk.Configuration, new_db: conffwk.Configuration)->None:
    """Consolidates ALL dal objects in db into new_db

    :param db: A conffwk.Configuration containing objects you want to copy over
    :param new_db: A conffwk.Configuration you want to copy objects into
    """    
    dal_list = list(db.get_all_dals().values())
    copy_dals_to_cfg(new_db, dal_list)

def consolidate_session(db: conffwk.Configuration, new_db: conffwk.Configuration, session_id: str)->None:
    """
    Consolidates all objects related to the session with id 'session_id' into a single file
    
    :param db: A conffwk.Configuration containing objects you want to copy over
    :param new_db: A conffwk.Configuration you want to copy objects into
    :param session_id: Name of session
    """

    # Check session exists and load
    try:
        dal_session = db.get_dal('Session', session_id)
    except Exception as e:
        log.exception(e)
        raise e
    
    dal_list = get_relationships(db, dal_session, [])
    copy_dals_to_cfg(new_db, dal_list)

def get_relationships(db: conffwk.Configuration, current_dal, dal_list):
    '''
    Recurssively get all objects related to current_dal
    '''
    dal_list.append(current_dal)
    
    for rel in db.relations(current_dal.className(), all=True):
        rel_obj = getattr(current_dal, rel, None)
        if rel_obj is None:
            continue
        
        if not isinstance(rel_obj, list):
            rel_obj = [rel_obj]
        
        for rel_obj in rel_obj:
            dal_list = get_relationships(db, rel_obj, dal_list)
        
    return dal_list


def copy_dals_to_cfg(new_db: conffwk.Configuration, dal_list)->None:
    '''
    Copy a list of dals into a configuration
    '''
    log.debug("Copying %d objects to new db", len(dal_list))
    for dal in dal_list:
        new_db.add_dal(dal)

    log.debug("Saving database")
    new_db.commit()
    
    
def copy_configuration(dest_dir : Path, input_files: list):
    if len(input_files) == 0:
        return []

    log.info(f"Copying configuration represented by databases: \'{input_files}\' to \'{dest_dir}\'")
    dest_dir = dest_dir.resolve() # Always include by absolute path when copying
    sys.setrecursionlimit(10000)  # for example

    output_dbs = []

    for input_file in input_files:
        db = conffwk.Configuration("oksconflibs:" + input_file)
        includes = db.get_includes(None)
        schemas = [i for i in includes if "schema.xml" in i]
        dbs = [i for i in includes if "data.xml" in i]
        newdbs = copy_configuration(dest_dir, dbs)

        output_file = dest_dir / os.path.basename(input_file)

        new_db = conffwk.Configuration("oksconflibs")
        new_db.create_db(str(output_file), schemas + newdbs)
        new_db.commit()

        dals = db.get_all_dals()

        for dal in dals:
            db.get_dal(dals[dal].className(), dals[dal].id)
            new_db.add_dal(dals[dal])

        new_db.commit()
        output_dbs.append(str(output_file))
    log.debug("DONE")

    return output_dbs


def consolidate_files(oksfile, *input_files):
    includes = []
    dbs = []
    str_in_files = '\n'.join(input_files)
    log.info(f"Consolidating {len(input_files)} databases into output database \'{oksfile}\'. Input databases: {str_in_files}")
    sys.setrecursionlimit(10000)  # for example

    for input_file in input_files:
        dbs.append(conffwk.Configuration("oksconflibs:" + input_file))
        includes += get_all_includes(dbs[len(dbs) - 1], None)

    includes = list(set(includes))
    includes = [i for i in includes if i not in input_files]
    log.debug(f"Included files: {includes}")

    new_db = conffwk.Configuration("oksconflibs")
    new_db.create_db(oksfile, includes)

    new_db.commit()

    for db in dbs:
        log.debug(f"Reading dal objects from old db {db}")
        dals = db.get_all_dals()

        log.debug(f"Copying objects to new db {new_db}")
        for dal in dals:

            try:
                new_db.get_dal(dals[dal].className(), dals[dal].id)
            except:
                new_db.add_dal(dals[dal])
            new_db.commit()

    log.debug(f"Saving database {new_db}")
    new_db.commit()