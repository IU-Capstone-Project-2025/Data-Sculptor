import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ToolbarButton } from '@jupyterlab/apputils';
import { DocumentRegistry } from '@jupyterlab/docregistry';
import { NotebookPanel, INotebookModel } from '@jupyterlab/notebook';
import { IDisposable } from '@lumino/disposable';
import * as nbformat from '@jupyterlab/nbformat'; // Import nbformat

const buttonExtension: JupyterFrontEndPlugin<void> = {
  id: 'notebook-rewriter',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    app.docRegistry.addWidgetExtension('Notebook', new ButtonExtension());
  }
};

class ButtonExtension implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel> {
  createNew(panel: NotebookPanel, context: DocumentRegistry.IContext<INotebookModel>): IDisposable {
    const button = new ToolbarButton({
      className: 'rewrite-notebook-btn',
      label: 'Rewrite Notebook',
      onClick: async () => {
        await this.rewriteNotebook(panel);
      },
      tooltip: 'Rewrite and save current notebook'
    });

    panel.toolbar.insertItem(10, 'rewriteNotebook', button);
    return button;
  }

  private async rewriteNotebook(panel: NotebookPanel): Promise<void> {
    const notebook = panel.content;
    const context = panel.context;

    if (!notebook.model) {
      console.error('No notebook model available');
      return;
    }

    try {
      // Get current content as nbformat.INotebookContent
      const current = notebook.model.toJSON();
      
      // Modify content
      const modified = this.transformContent(current);
      
      // Update model
      notebook.model.fromJSON(modified);
      
      // Save to disk
      await context.save();
      console.log('Notebook updated successfully!');
    } catch (error) {
      console.error('Error rewriting notebook:', error);
    }
  }

  // Updated with proper type annotation
  private transformContent(notebook: nbformat.INotebookContent): nbformat.INotebookContent {
    // Example transformation: Add metadata and new cell
    return {
      ...notebook,
      cells: [
        {
          cell_type: 'code',
          execution_count: null,
          metadata: {},
          outputs: [],
          source: [
            '# Added by JupyterLab Extension\n',
            'print("Notebook processed successfully!")'
          ]
        } as nbformat.ICodeCell,
        ...notebook.cells
      ],
      metadata: {
        ...notebook.metadata,
        rewritten: true,
        processed_date: new Date().toISOString()
      }
    };
  }
}

export default buttonExtension;