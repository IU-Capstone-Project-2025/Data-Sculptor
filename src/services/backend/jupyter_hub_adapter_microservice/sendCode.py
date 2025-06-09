from http.client ***REMOVED***sponses

from IPython.core.magic import Magics, magics_class, cell_magic

***REMOVED***quests
import os

from dotenv import load_dotenv
load_dotenv()

@magics_class
class tellBackendMagic(Magics):

    @cell_magic
    def LLM_Validation(self, line, cell):
        file_path = line.strip()
        self.path_is_valid(file_path)
        backend_URL = os.getenv("LLM_VALIDATOR_URL")
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{backend_URL}/mdAnswer", files=files)
            
            with open(f"{os.path.dirname(file_path)}/response.md", "wb") as f:
                f.write(response.content)
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {e}")

    def path_is_valid(self, file_path):
        if not os.path.isfile(file_path):
            raise Exception("Please, provide path to a valid file")


def load_ipython_extension(ipython):
    ipython.register_magics(tellBackendMagic)
