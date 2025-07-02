import '../style/index.css';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { addCellButton } from './syntacticButton';
import { createToolbarButton } from './semanticButton';
import { API_ENDPOINT } from './config';


// Get environment variable during build time
// const API_ENDPOINT = process.env.LLM_VALIDATOR_URL || 'http://127.0.0.1:9001';

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'combined-validation-plugin:plugin',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app, tracker: INotebookTracker) => {
    console.log('[Combined Validation] Plugin activated');
    console.log(`[Notebook Validation] Using endpoint: ${API_ENDPOINT || 'NOT CONFIGURED'}`);

    // Track seen cells for per-cell validation
    const seenCells = new WeakSet<any>();

    // ========== PANEL MANAGEMENT ==========
    const hookPanel = (panel: NotebookPanel) => {
      // Add toolbar button
      const toolbarButton = createToolbarButton(panel);
      panel.toolbar.insertItem(10, 'notebookValidation', toolbarButton);
      
      // Add cell buttons
      panel.sessionContext.ready.then(() => {
        panel.content.widgets.forEach(cell => addCellButton(cell, panel, seenCells));
        
        // Handle new cells
        panel.content.model.cells.changed.connect((_, args) => {
          if (args.type === 'add' && Array.isArray(args.newValues)) {
            for (const model of args.newValues) {
              const widget = panel.content.widgets.find(c => c.model === model);
              if (widget) addCellButton(widget, panel, seenCells);
            }
          }
        });
      });
    };

    // ========== INITIALIZATION ==========
    // Hook existing panels
    app.restored.then(() => {
      tracker.forEach(panel => hookPanel(panel));
    });
    
    // Hook new panels
    tracker.widgetAdded.connect((_, panel) => {
      hookPanel(panel);
    });
  }
};

export default plugin;