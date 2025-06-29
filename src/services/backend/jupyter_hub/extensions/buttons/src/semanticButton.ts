import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { ToolbarButton } from '@jupyterlab/apputils';
import { rewriteNotebook, saveFeedbackFile } from './fileManager'

import { API_ENDPOINT } from './config';

// import { LabIcon } from '@jupyterlab/ui-components'

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
// ========== TOOLBAR BUTTON IMPLEMENTATION ==========
export const createToolbarButton = (panel: NotebookPanel) => {

  const button = new ToolbarButton({
    className: 'validation-toolbar-button',
    iconClass: 'jp-RefreshIcon',
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
        console.log("[Notebook Validation] Preapring notebook data");
        const context = panel.context;
        const notebookContent = await context.model.toJSON();
    
        // 4. PREPARE JSON BODY
        const payload = {
            current_code: JSON.stringify(notebookContent)
                .replace(/\\n/g, '\n')  // Replace double-escaped \\n with single \n
        };

        console.log("[Notebook Validation] Sending payload:");
        console.log(payload);

        // 5. SEND VALIDATION REQUEST
        const response = await fetch(`${API_ENDPOINT}/api/v1/feedback`, {
            method: 'POST',
            body: JSON.stringify(payload),  // Send as raw JSON string
            headers: {
                'Content-Type': 'application/json',  // Required header
                'Accept': 'application/json'
            },
            signal: AbortSignal.timeout(30000)  // 30s timeout
        });

        console.log("[notebook validation] fetched response");
        // 6. HANDLE RESPONSE ERRORS
        if (!response.ok) {
          try {
            // Attempt to parse JSON error response
            const errorData = await response.json();
            throw new Error(`HTTP ${response.status}: ${JSON.stringify(errorData)}`);
          } catch {
            // Fallback to text if JSON parsing fails
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
          }
        }
        console.log("[notebook validation] Response ok");

        // 7. PROCESS SUCCESSFUL RESPONSE
        const result = await response.json();  // Parse JSON response

        const resultText = result.non_localized_feedback;
        if (resultText === null) {
          throw new Error("md feedback lost");
        }
        const resultLSP = result.localized_feedback;
        if (resultText === null) {
          throw new Error("lsp feedback lost");
        }
    
        // 8. SHOW SUCCESS STATE
        // button.icon = defaultIcon;
        // button.node.title = 'Semantic validation successful!';
        // button.node.classList.add('success');

        // 8. SAVE TO JUPYTERHUB FILE SYSTEM
        const savedFilePath = await saveFeedbackFile(panel.context.path, resultText);


        // 9. SHOW SUCCESS STATE
        console.log(`Feedback saved to: ${savedFilePath}`);
        console.log("LSP:");
        console.log(resultLSP);
        // button.icon = defaultIcon;
        // button.node.title = `Feedback saved to ${fileName}!`;
        // button.node.classList.add('success');

        // 10. REWRITE NOTEBOOK FILE 

        await rewriteNotebook(panel, resultLSP);
    
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