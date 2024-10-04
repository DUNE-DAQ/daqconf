import os
import glob

def find_oksincludes(includes:list[str], extra_dirs:list[str] = []):
    includefiles = []

    searchdirs = [path for path in os.environ["DUNEDAQ_DB_PATH"].split(":")]
    for dir in extra_dirs:
        searchdirs.append(dir)

    for inc in includes:
        # print (f"Searching for {inc}")
        match = False
        inc = inc.removesuffix(".xml")
        if inc.endswith(".data"):
            sub_dirs = ["config", "data"]
        elif inc.endswith(".schema"):
            sub_dirs = ["schema"]
        else:
            sub_dirs = ["*"]
            inc = inc + "*"
        for path in searchdirs:
            # print (f"   {path}/{inc}.xml")
            matches = glob.glob(f"{inc}.xml", root_dir=path)
            if len(matches) == 0:
                for search_dir in sub_dirs:
                    # print (f"   {path}/{search_dir}/{inc}.xml")
                    matches = glob.glob(f"{search_dir}/{inc}.xml", root_dir=path)
                    for filename in matches:
                        if filename not in includefiles:
                            print(f"Adding {filename} to include list")
                            includefiles.append(filename)
                        #else:
                        #    print(f"{filename} already in include list")
                        match = True
                        break
                    if match:
                        break
                if match:
                    break
            else:
                for filename in matches:
                    if filename not in includefiles:
                        print(f"Adding {filename} to include list")
                        includefiles.append(filename)
                    #else:
                    #    print(f"{filename} already in include list")
                    match = True
                    break

        if not match:
            print(f"Error could not find include file for {inc}")
            return [False, []]

    return [True, includefiles]
