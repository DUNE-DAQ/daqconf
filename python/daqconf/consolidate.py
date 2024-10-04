from pathlib import Path
import conffwk
import sys
import os


def get_all_includes(db, file):
    includes = db.get_includes(file)
    for include in includes:
        if "data.xml" in include:
            includes += get_all_includes(db, include)

    return list(set(includes))


def consolidate_db(oksfile, output_file):
    sys.setrecursionlimit(10000)  # for example
    print("Reading database")
    db = conffwk.Configuration("oksconflibs:" + oksfile)

    schemafiles = []
    includes = get_all_includes(db, None)
    schemafiles += [i for i in includes if "schema.xml" in i]
    print(f"Included schemas: {schemafiles}")

    print("Creating new database")
    new_db = conffwk.Configuration("oksconflibs")
    new_db.create_db(output_file, schemafiles)

    new_db.commit()

    print("Reading dal objects from old db")
    dals = db.get_all_dals()

    print(f"Copying objects to new db")
    for dal in dals:

        # print(f"Loading object {dal} into cache")
        db.get_dal(dals[dal].className(), dals[dal].id)

        # print(f"Copying object: {dal}")
        new_db.add_dal(dals[dal])

    print("Saving database")
    new_db.commit()
    print("DONE")

def copy_configuration(dest_dir : Path, input_files: list):
    if len(input_files) == 0:
        return []

    print(f"Copying configuration represented by databases: {input_files} to {dest_dir}")
    dest_dir = dest_dir.resolve() # Always include by absolute path when copying
    sys.setrecursionlimit(10000)  # for example

    output_dbs = []

    for input_file in input_files:
        db = conffwk.Configuration("oksconflibs:" + input_file)
        includes = db.get_includes(None)
        schemas = [i for i in includes if "schema.xml" in i]
        dbs = [i for i in includes if "data.xml" in i]
        newdbs = copy_configuration(dest_dir, dbs)

        #print("Creating new database")
        output_file = dest_dir / os.path.basename(input_file)

        new_db = conffwk.Configuration("oksconflibs")
        new_db.create_db(str(output_file), schemas + newdbs)
        new_db.commit()

        #print("Reading dal objects from old db")
        dals = db.get_all_dals()

        #print(f"Copying objects to new db")
        for dal in dals:

            # print(f"Loading object {dal} into cache")
            db.get_dal(dals[dal].className(), dals[dal].id)

            # print(f"Copying object: {dal}")
            new_db.add_dal(dals[dal])

        #print("Saving database")
        new_db.commit()
        output_dbs.append(str(output_file))
    print("DONE")
        
    return output_dbs


def consolidate_files(oksfile, *input_files):
    includes = []
    dbs = []

    print(f"Consolidating {len(input_files)} databases into output database {oksfile}. Input databases: {input_files}")
    sys.setrecursionlimit(10000)  # for example

    for input_file in input_files:
        dbs.append(conffwk.Configuration("oksconflibs:" + input_file))
        includes += get_all_includes(dbs[len(dbs) - 1], None)
        
    includes = list(set(includes))
    includes = [i for i in includes if i not in input_files]    
    print(f"Included files: {includes}")

    new_db = conffwk.Configuration("oksconflibs")
    new_db.create_db(oksfile, includes)

    new_db.commit()

    for db in dbs:
        print(f"Reading dal objects from old db {db}")
        dals = db.get_all_dals()

        print(f"Copying objects to new db {new_db}")
        for dal in dals:

            try: 
                new_db.get_dal(dals[dal].className(), dals[dal].id)
                #print(f"ERROR: Database already contains object {dal}")  
            except:            
                # print(f"Copying object: {dal}")
                new_db.add_dal(dals[dal])
            new_db.commit()

    print(f"Saving database {new_db}")
    new_db.commit()