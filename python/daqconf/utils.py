import glob
import logging
import os
import socket
from rich.logging import RichHandler


log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_logging(level:str="INFO"):
    level = level.upper()

    loglevel = logging.INFO

    match level:
        case "DEBUG":
            loglevel = logging.DEBUG
        case "INFO":
            loglevel = logging.INFO
        case "WARNING":
            loglevel = logging.WARNING
        case "ERROR":
            loglevel = logging.ERROR
        case "CRITICAL":
            loglevel = logging.CRITICAL
        case _:
            loglevel = logging.INFO

    FORMAT = "%(message)s"
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )
    logging.getLogger().setLevel(loglevel)


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

def find_free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]
        s.close()
        return port
