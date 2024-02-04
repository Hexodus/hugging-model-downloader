#!/usr/bin/env python3
from pypdl import Downloader
from urllib.parse import urlparse
from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError
import requests
import fire
from sty import bg, ef, fg, rs

def get_redirect_header(url):
    session = requests.Session()
    response = session.get(url, allow_redirects=False)
    redirect_url = response.headers.get('Location')
    return url if redirect_url is None else redirect_url

def get_filenames(model_name, quant, branch = None):
    api = HfApi()
    
    try:
        branches = api.list_repo_refs(model_name).branches
        if branch is None:
            branch = branches[0].name
        else:
            is_valid_branch_name = any(b.name == branch for b in branches)
            if not is_valid_branch_name:
                print(fg.red + 'Branch not found: ', branch, 'Defaulting to first found branch.', fg.rs)
                branch = branches[0].name

        files = api.list_files_info(model_name)
        found = False
        for file_info in files:
            if (file_info.rfilename.find(quant) != -1 or quant == '*'):
                found = True
                yield branch, file_info.rfilename
        
        if not found:
            print(fg.red + 'Quant not found: ' + quant, fg.rs)
            return None, None
    except RepositoryNotFoundError:
        print(fg.red + 'Model not found: ', model_name, fg.rs)
        return None, None

def build_url(model_name, branch, filename):
    return f'https://huggingface.co/{model_name}/resolve/{branch}/{filename}'

def parallel_download(lfs_url, target, filename):
    file_path = ""
    if len(target) > 0 :
        if not target.endswith('/'):
            target = target + '/'
        file_path = target + filename
    else:
        file_path = filename
    dl = Downloader()
    dl.start(lfs_url, file_path)

def parse_model_name(model_name: str, quant: str, branch: str):
    """Parse model_name to check if it's a URL and extract parameters if so"""
    parsed_url = urlparse(model_name)
    if parsed_url.scheme and parsed_url.netloc:
        # model_name is a URL
        path_parts = parsed_url.path.strip('/').split('/')
        model_name = "/".join(path_parts[0:2])
        branch = path_parts[3] if len(path_parts) > 3 else branch
        filename = path_parts[4] if len(path_parts) > 4 else ""
        quant = filename.split('.')[1] if '.' in filename else quant
    return model_name, quant, branch

def download_model(model_name : str, quant : str = "none", branch : str = "", target: str = ""):
    """ Downloads a quantized model from hugging face hub using parallel download streams"""
    model_name, quant, branch = parse_model_name(model_name, quant, branch)
    for branch, filename in get_filenames(model_name, quant, branch if branch else None):
        if filename is None: break
        url = build_url(model_name, branch, filename)
        print(fg.green + f"Downloading {filename} from {url}" + fg.rs)
        print(fg.yellow + "/n") # set to new line and yellow color
        lfs_url = get_redirect_header(url)
        parallel_download(lfs_url, target, filename)
        print(fg.rs +"/n") # Set back to default color
        print(fg.green + f"Downloaded {filename}" + fg.rs)
        
if __name__ == "__main__":
    fire.Fire(download_model)
