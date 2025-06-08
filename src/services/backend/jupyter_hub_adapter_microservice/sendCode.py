from http.client import responses

from IPython.core.magic import Magics, magics_class, cell_magic

import requests
import os

from dotenv import load_dotenv
load_dotenv()

@magics_class
class tellBackendMagic(Magics):

    @cell_magic
    def LLM_Validation(self, line, cell):

        working_dir = line.strip()
        self.path_is_valid(working_dir)
        backend_URL = os.getenv("LLM_VALIDATOR_URL")
        try:
            response = requests.post(f"{backend_URL}/mdAnswer", json={"code": cell})
            with open(f"{working_dir}/response.md", "w") as f:
                md_response = response.json().get("content")
                f.write(md_response)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {e}")

    def path_is_valid(self, working_dir):
        if not os.path.isdir(working_dir):
            raise Exception("Please, provide path to working directory")


def load_ipython_extension(ipython):
    ipython.register_magics(tellBackendMagic)
