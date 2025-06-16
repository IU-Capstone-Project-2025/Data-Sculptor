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


def load_ipython_extension(ipython):
    ipython.register_magics(AnalyzeMagic)