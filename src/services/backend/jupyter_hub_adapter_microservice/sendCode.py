from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.display import Javascript, display


@magics_class
class AnalyzeMagic(Magics):
    @cell_magic
    def syntactic_analyze(self, line, cell):
        js = r'''
        (function(){
            if (window.Jupyter && Jupyter.notebook) {
                Jupyter.notebook.save_checkpoint();
            } else {
                const btn = document.querySelector('[data-command="docmanager:save"]');
                if (btn) btn.click();
            }
        })();
        '''
        display(Javascript(js))
        print("💾 Notebook saved; static analysis will run on save.")
    
    @cell_magic
    def LLM_Validation(self, line, cell):
        file_path = line.strip()
        self.path_is_valid(file_path)
        backend_URL = os.getenv("LLM_VALIDATOR_URL")
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{backend_URL}/getMdFeedback", files=files)
            
            with open(f"{os.path.dirname(file_path)}/response.md", "wb") as f:
                f.write(response.content)
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {e}")


def load_ipython_extension(ipython):
    ipython.register_magics(AnalyzeMagic)