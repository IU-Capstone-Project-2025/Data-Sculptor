import '../style/index.css';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { ToolbarButton } from '@jupyterlab/apputils';
// import { LabIcon } from '@jupyterlab/ui-components'
import { API_ENDPOINT } from './config';

const CHECK_SVG = `
<svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <path fill="currentColor" d="M6.003 11.803L2.2 8l1.2-1.2 2.603 2.603L12.6 3.8l1.2 1.2z"/>
</svg>`;

const SPINNER_SVG = `
<svg viewBox="0 0 50 50" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25" cy="25" r="20" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
</svg>`;

// const defaultIcon = new LabIcon({
//   name: 'validation:check-icon',
//   svgstr: CHECK_SVG
// });
// 
// const loadingIcon = new LabIcon({
//   name: 'validation:loading-icon',
//   svgstr: SPINNER_SVG
// });
// 
// const errorIcon = new LabIcon({
//   name: 'validation:error-icon',
//   svgstr: `<svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
//     <path fill="currentColor" d="M14.7 2.7L13.3 1.3 8 6.6 2.7 1.3 1.3 2.7 6.6 8l-5.3 5.3 1.4 1.4L8 9.4l5.3 5.3 1.4-1.4L9.4 8z"/>
//   </svg>`
// });

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

    // ========== TOOLBAR BUTTON IMPLEMENTATION ==========
    const createToolbarButton = (panel: NotebookPanel) => {

      const button = new ToolbarButton({
        className: 'validation-toolbar-button',
        iconClass: 'jp-CheckIcon',
        onClick: async () => {
          console.log('[Notebook Validation] Processing notebook');
      
          // 1. Preserve original state
          // const originalIcon = button.icon;
          // const originalTitle = button.node.title;
      
          // 2. Show loading state
          // button.icon = loadingIcon;
          // button.node.title = 'Analyzing notebook semantics...';
          // button.node.classList.add('spinning');

          try {
            // 3. PREPARE NOTEBOOK DATA
            const context = panel.context;
            const notebookContent = await context.model.toJSON();
        
            // 4. BUILD FORM DATA
            const formData = new FormData();
            const notebookBlob = new Blob(
              [JSON.stringify(notebookContent)], 
              { type: 'application/json' }
            );
            formData.append('file', notebookBlob, 'notebook.ipynb');

            // 5. SEND VALIDATION REQUEST
            const response = await fetch(`${API_ENDPOINT}/getMdFeedback`, {
              method: 'POST',
              body: formData,
              signal: AbortSignal.timeout(30000)  // 30s timeout
            });

            // 6. HANDLE RESPONSE ERRORS
            if (!response.ok) {
              const errorText = await response.text();
              throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            // 7. PROCESS SUCCESSFUL RESPONSE
            const resultBlob = await response.blob();
            const resultText = await resultBlob.text();
        
            // 8. SHOW SUCCESS STATE
            // button.icon = defaultIcon;
            // button.node.title = 'Semantic validation successful!';
            // button.node.classList.add('success');
        
            console.log('Received Markdown feedback:', resultText.substring(0, 100) + '...');
        
          } catch (error) {
            // 9. HANDLE VALIDATION FAILURES
            console.error('[Notebook Validation] Validation failed:', error);
            // button.icon = errorIcon;
            // button.node.title = `Error: ${error.message || 'Request failed'}`;
            // button.node.classList.add('error');
        
            // 10. ERROR MESSAGE HANDLING
            let errorMessage = 'Request failed';
            if (error.name === 'AbortError') {
              errorMessage = 'Request timed out (30s)';
            } else if (error.message.includes('Failed to fetch')) {
              errorMessage = 'CORS error: Check server configuration';
            } else {
              errorMessage = error.message || 'Request failed';
            }
        
            // button.node.title = `Error: ${errorMessage}`;
          } finally {
            // 11. CLEANUP ANIMATIONS
            // button.node.classList.remove('spinning');
        
            // 12. RESET TO ORIGINAL STATE AFTER DELAY
            setTimeout(() => {
              // button.icon = originalIcon;
              // button.node.title = originalTitle;
              // button.node.classList.remove('success', 'error');
            }, 3000);  // Reset after 3 seconds
          }
        },
        tooltip: 'Validate notebook semantics'  // Initial tooltip
      });
  
      return button;
    };


    // ========== PER-CELL BUTTON FUNCTIONALITY ==========
    const addCellButton = (cell: any, panel: NotebookPanel) => {
      if (cell.model.type !== 'code' || seenCells.has(cell)) {
        return;
      }
      
      const prompt = cell.node.querySelector('.jp-CellPrompt') || 
                    cell.node.querySelector('.jp-InputArea-prompt');
      if (!prompt) return;

      const wrap = document.createElement('span');
      wrap.className = 'validate-btn-wrapper';
      wrap.innerHTML = CHECK_SVG;
      wrap.title = 'Validate this cell';
      
      wrap.onclick = () => {
        console.log('[Cell Validation] clicked cell', cell.model.id);
        wrap.innerHTML = SPINNER_SVG;
        wrap.classList.add('spinning');
        
        // Set spinner duration
        const spinner = wrap.querySelector('svg');
        if (spinner && spinner.style) {
            spinner.style.animationDuration = '5s';
        }
        
        // Actual validation logic would go here
        panel.context.save()
          .then(() => {
            wrap.classList.remove('spinning');
            wrap.innerHTML = CHECK_SVG;
            wrap.style.color = 'green';
          })
          .catch((error) => {
            console.error('[Cell Validation] Failed:', error);
            wrap.innerHTML = '✖';
            wrap.style.color = 'red';
          });
      };

      prompt.insertAdjacentElement('afterend', wrap);
      seenCells.add(cell);
    };

    // ========== PANEL MANAGEMENT ==========
    const hookPanel = (panel: NotebookPanel) => {
      // Add toolbar button
      const toolbarButton = createToolbarButton(panel);
      panel.toolbar.insertItem(10, 'notebookValidation', toolbarButton);
      
      // Add cell buttons
      panel.sessionContext.ready.then(() => {
        panel.content.widgets.forEach(cell => addCellButton(cell, panel));
        
        // Handle new cells
        panel.content.model.cells.changed.connect((_, args) => {
          if (args.type === 'add' && Array.isArray(args.newValues)) {
            for (const model of args.newValues) {
              const widget = panel.content.widgets.find(c => c.model === model);
              if (widget) addCellButton(widget, panel);
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