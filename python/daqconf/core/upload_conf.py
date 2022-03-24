from appfwk.conf_utils import write_json_files
import requests
from pathlib import Path
import tempfile
import os
import json
from rich.console import Console

console = Console()

def get_json_recursive(path):
  data = {
    'files':[],
    'dirs':[],
  }

  for filename in os.listdir(path):
    if os.path.isdir(path/filename):
      dir_data = {
        'name' : filename,
        'dir_content': get_json_recursive(path/filename)
      }
      data['dirs'].append(dir_data)
      continue

    if not filename[-5:] == ".json":
      console.log(f'WARNING! Ignoring {path/filename} as this is not a json file!')
      continue

    with open(path/filename,'r') as f:
      file_data = {
        "name": filename[0:-5],
        "configuration": json.load(f)
      }
      data['files'].append(file_data)
  return data



def upload_conf(url, app_command_datas, system_command_datas, name, verbose):
    docid=0
    version=0
    coll_name=0
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        json_dir = Path(tmpdirname)/name
        write_json_files(app_command_datas, system_command_datas, json_dir, verbose=verbose)

        conf_data = get_json_recursive(json_dir)
        
        header = {
            'Accept' : 'application/json',
            'Content-Type':'application/json'
        }

        response = requests.post(
            'http://'+url+'/create?collection='+name,
            headers=header,
            data=json.dumps(conf_data)
        )
        resp_data = response.json()
        
        if verbose:
            console.log(f"conf service responded with {resp_data}")
        if not resp_data['success']:
            raise RuntimeError(f'Couldn\'t upload your configuration: {resp_data["error"]}')
        docid=resp_data['docid']
        version=resp_data['version']
        coll_name=resp_data['coll_name']
        

    return docid, coll_name, version
