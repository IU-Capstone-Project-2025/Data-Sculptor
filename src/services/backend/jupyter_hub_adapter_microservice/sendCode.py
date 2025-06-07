from http.client import responses

from IPython.core.magic import Magics, magics_class, cell_magic

import requests
import os


@magics_class
class tellBackendMagic:

    @cell_magic
    def LLM_Validation(self, line, cell):

        working_dir = line.strip()
        self.path_is_valid(working_dir)
        backend_URL = ...
        try:
            response = requests.post(backend_URL, json={"code": cell})
            with open(f"{working_dir}/response.md") as f:
                # md_response = response.json().get("content")
                md_response = "MD response from Aziz!!!"
                f.write(md_response)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {e}")

    def path_is_valid(self, working_dir):
        if os.path.isdir(working_dir):
            raise Exception("Please, provide path to working directory")


def load_ipython_extension(ipython):
    ipython.register_magics(tellBackendMagic)