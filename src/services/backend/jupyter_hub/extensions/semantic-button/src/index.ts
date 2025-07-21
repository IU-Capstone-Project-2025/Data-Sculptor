/*
  ВАЖНО!!!
  ЭНДПОИНТ ЗАХАРДКОЖЕН!!!
  я не разорбался...

  - Марат
*/
import '../style/index.css';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { ToolbarButton } from '@jupyterlab/apputils';

const CHECK_SVG = `
<svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <path fill="currentColor" d="M6.003 11.803L2.2 8l1.2-1.2 2.603 2.603L12.6 3.8l1.2 1.2z"/>
</svg>`;

const SPINNER_SVG = `
<svg viewBox="0 0 50 50" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25" cy="25" r="20" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
</svg>`;

// Use the external feedback service port (accessible from browser)
const API_ENDPOINT = 'http://localhost:11004';

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'semantic-button-per-cell:plugin',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app, tracker: INotebookTracker) => {
    console.log('[semantic-button] activated');
    console.log(`[semantic-button] Using endpoint: ${API_ENDPOINT || 'NOT CONFIGURED'}`);

    // Создаем кнопку для тулбара
    const createToolbarButton = (panel: NotebookPanel) => {
      const button = new ToolbarButton({
        className: 'semantic-toolbar-button',
        iconClass: 'jp-CheckIcon',
        onClick: async () => {
          console.log('[semantic-button] Processing notebook');
          
          // Сохраняем оригинальный контент кнопки
          const originalHTML = button.node.innerHTML;
          const originalTitle = button.node.title;
          
          // Показываем спиннер
          button.node.innerHTML = SPINNER_SVG;
          button.node.classList.add('spinning');
          button.node.title = 'Analyzing semantics...';
          
          try {
            // Get all cells from the notebook
            const context = panel.context;
            const notebook = context.model;
            
            // Collect all code cells
            let allCode = '';
            for (let i = 0; i < notebook.cells.length; i++) {
              const cell = notebook.cells.get(i);
              if (cell.type === 'code') {
                allCode += cell.value.text + '\n\n';
              }
            }
            
            if (!allCode.trim()) {
              throw new Error('No code cells found in notebook');
            }

            // Send request to feedback service
            const response = await fetch(API_ENDPOINT + '/api/v1/feedback', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                current_code: allCode,
                cell_code_offset: 0,
                section_index: 0,
                profile_index: "00000000-0000-0000-0000-000000000000", // Default UUID
                use_deep_analysis: true
              }),
              signal: AbortSignal.timeout(30000) // 30s timeout
            });

            if (!response.ok) {
              const errorText = await response.text();
              throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            // Parse JSON response
            const result = await response.json();
            
            console.debug('[semantic-button] API response received:', result);

            // Визуальная обратная связь
            button.node.innerHTML = CHECK_SVG;
            button.node.style.color = 'green';
            button.node.title = 'Semantic validation successful!';
            
            // Display feedback in console
            console.log('Received feedback:', result.non_localized_feedback || 'No feedback provided');
            
          } catch (error) {
            console.error('[semantic-button] Validation failed:', error);
            button.node.innerHTML = '✖';
            button.node.style.color = 'red';
            
            // Улучшенное сообщение об ошибке
            let errorMessage = 'Request failed';
            if (error.name === 'AbortError') {
              errorMessage = 'Request timed out (30s)';
            } else if (error.message.includes('Failed to fetch')) {
              errorMessage = 'CORS error: Check server configuration';
            } else {
              errorMessage = error.message || 'Request failed';
            }
            
            button.node.title = `Error: ${errorMessage}`;
          } finally {
            button.node.classList.remove('spinning');
            
            // Возвращаем исходное состояние через 3 секунды
            setTimeout(() => {
              button.node.innerHTML = originalHTML;
              button.node.style.color = '';
              button.node.title = originalTitle;
            }, 3000);
          }
        },
        tooltip: 'Validate notebook semantics'
      });
      
      return button;
    };

    // Добавляем кнопку в тулбар панели
    const addButtonToToolbar = (panel: NotebookPanel) => {
      const button = createToolbarButton(panel);
      panel.toolbar.insertItem(10, 'semanticValidation', button);
      return button;
    };

    // Обработчик для панелей
    const hookPanel = (panel: NotebookPanel) => {
      addButtonToToolbar(panel);
    };

    // Добавляем кнопку в существующие панели
    app.restored.then(() => {
      tracker.forEach(panel => {
        hookPanel(panel);
      });
    });
    
    // Добавляем кнопку в новые панели
    tracker.widgetAdded.connect((_, panel) => {
      hookPanel(panel);
    });
  }
};

export default plugin;