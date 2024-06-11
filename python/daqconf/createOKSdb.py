import conffwk
import os
import glob


def generate_file(oksfile, include):
    """Simple script to create an 'empty' OKS file.
    The file will automatically include the confmodel schema
    and any other OKS files you specify"""

    includefiles = ["schema/confmodel/dunedaq.schema.xml"]

    searchdirs = [path for path in os.environ["DUNEDAQ_DB_PATH"].split(":")]
    searchdirs.append(os.path.dirname(oksfile))
    for inc in include:
        # print (f"Searching for {inc}")
        match = False
        inc = inc.removesuffix(".xml")
        if inc.endswith(".data"):
            ftype = "data"
        elif inc.endswith(".schema"):
            ftype = "schema"
        else:
            ftype = "*"
            inc = inc + "*"
        for path in searchdirs:
            matches = glob.glob(f"{inc}.xml", root_dir=path)
            if len(matches) == 0:
                matches = glob.glob(f"{ftype}/{inc}.xml", root_dir=path)
            for filename in matches:
                print(f"Adding {filename} to include list")
                includefiles.append(filename)
                match = True
            if match:
                break
        if not match:
            print(f"Error could not find include file for {inc}")
            return
    db = conffwk.Configuration("oksconflibs")
    if not oksfile.endswith(".data.xml"):
        oksfile = oksfile + ".data.xml"
    print(f"Creating OKS database file {oksfile}")
    db.create_db(oksfile, includefiles)
    db.commit()
