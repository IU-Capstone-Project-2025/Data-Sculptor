import '../style/index.css';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';

const CHECK_SVG = `
<svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <path fill="currentColor" d="M6.003 11.803L2.2 8l1.2-1.2 2.603 2.603L12.6 3.8l1.2 1.2z"/>
</svg>`;

const SPINNER_SVG = `
<svg viewBox="0 0 50 50" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25" cy="25" r="20" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
</svg>`;

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'validate-button-per-cell:plugin',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app, tracker: INotebookTracker) => {
    console.log('[validate-button] activated (SVG + 10s spinner)');

    const seen = new WeakSet<any>();

    function addCellButton(cell: any, panel: NotebookPanel) {
      if (cell.model.type !== 'code' || seen.has(cell)) {
        return;
      }
      const prompt =
        cell.node.querySelector('.jp-CellPrompt') ??
        cell.node.querySelector('.jp-InputArea-prompt');
      if (!prompt) {
        return;
      }

      const wrap = document.createElement('span');
      wrap.className = 'validate-btn-wrapper';
      wrap.innerHTML = CHECK_SVG;
      wrap.title = 'Validate this cell';
      wrap.onclick = () => {
        console.log('[validate-button] clicked cell', cell.model.id);
        // показываем спиннер
        wrap.innerHTML = SPINNER_SVG;
        wrap.classList.add('spinning');
        // inline задаём длительность 10s
        const spinner = wrap.querySelector('svg');
        if (spinner && (spinner as any).style) {
          (spinner as any).style.animationDuration = '5s';
        }
        // Get the cell source code
        const cellCode = cell.model.value.text;
        
        // Get the feedback service URL from environment
        const feedbackUrl = process.env.URL_FEEDBACK_SERVICE || 'http://feedback-service:9352';
        
        // Send validation request to feedback service
        fetch(`${feedbackUrl}/generate_feedback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code: cellCode,
            language: 'python'
          })
        })
          .then(response => response.json())
          .then(data => {
            wrap.classList.remove('spinning');
            if (data.feedback && data.feedback.length > 0) {
              // Show feedback
              wrap.innerHTML = '📝';
              wrap.title = `Feedback: ${data.feedback}`;
              wrap.style.color = 'orange';
            } else {
              // No issues found
              wrap.innerHTML = CHECK_SVG;
              wrap.style.color = 'green';
              wrap.title = 'Code looks good!';
            }
          })
          .catch((error) => {
            console.error('Validation error:', error);
            wrap.classList.remove('spinning');
            wrap.innerHTML = '✖';
            wrap.style.color = 'red';
            wrap.title = 'Validation failed';
          });
      };

      prompt.insertAdjacentElement('afterend', wrap);
      seen.add(cell);
    }

    function hookPanel(panel: NotebookPanel) {
      panel.sessionContext.ready.then(() => {
        panel.content.widgets.forEach(cell => addCellButton(cell, panel));
        panel.content.model.cells.changed.connect((_, args) => {
          if (args.type === 'add' && Array.isArray(args.newValues)) {
            for (const model of args.newValues) {
              const w = panel.content.widgets.find(c => c.model === model);
              if (w) {
                addCellButton(w, panel);
              }
            }
          }
        });
      });
    }

    app.restored.then(() => {
      const current = tracker.currentWidget;
      if (current) {
        console.log('[validate-button] hooking current panel');
        hookPanel(current);
      }
    });
    tracker.widgetAdded.connect((_, panel) => {
      console.log('[validate-button] new notebook opened, hooking panel');
      hookPanel(panel);
    });
  }
};

export default plugin;
