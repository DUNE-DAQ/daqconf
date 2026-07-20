
from os.path import exists, abspath, dirname, expandvars
from urllib.parse import urlparse, parse_qsl

from daq_assettools.asset_file import AssetFile
from daq_assettools.asset_database import Database
from sqlite3 import OperationalError


def resolve_asset_file(data_file: str, verbose: bool = False) -> str:
    """
    Resolves a data file URI to an absolute file path. The data file can be specified as
        - An asset URI (e.g., asset://?name=frames)
        - A file URI (e.g., file:///path/to/frames.bin)
        - A local file path (e.g., /path/to/frames.bin)
    
    Args:
        data_file (str): The data file URI or path to resolve.
        verbose (bool): If True, prints additional information during resolution.

    Returns:
        str: The absolute path to the resolved data file.

    Raises:
        RuntimeError: If the data file cannot be found or resolved.
    """
    data_file_url = urlparse(data_file)

    if verbose:
        print(f"Checking asset URI {data_file_url}")

    if data_file_url.scheme == 'asset':
        asset_query = dict(parse_qsl(data_file_url.query))
        asset_db = Database(
            '/cvmfs/dunedaq.opensciencegrid.org/assets/dunedaq-asset-db.sqlite'
        )
        asset_query['status'] = 'valid'

        try:
            files = asset_db.get_files(asset_query)
            if not files:
                raise RuntimeError(
                    f"Couldn\'t find a valid asset for the query {data_file_url.query}"
                )

            elif len(files)>1:
                print(
                    f"Found {len(files)} assets in {dirname(asset_db.database_file)}, "
                    "taking the first one"
                )

            if verbose:
                print(f"Found asset in {dirname(asset_db.database_file)}")

            root_dir = dirname(asset_db.database_file)
            return f'{root_dir}/{files[0]["path"]}/{files[0]["name"]}'

        except OperationalError:
            raise RuntimeError(f"Couldn\'t find the asset {data_file}")


    elif data_file_url.scheme == 'file':
        filename = abspath(data_file_url.netloc+data_file_url.path)

        if not exists(filename):
            raise RuntimeError(f'Cannot find the frames.bin file {filename}')

        if verbose:
            print(f"Found asset in {dirname(filename)}")

        return filename

    resolved_data_file = abspath(expandvars(data_file))
    if resolved_data_file != '' and not exists(resolved_data_file):
        raise RuntimeError(f'Cannot find the frames.bin file {data_file}')

    if verbose:
        print(f"Found asset in {dirname(resolved_data_file)}")

    return resolved_data_file
