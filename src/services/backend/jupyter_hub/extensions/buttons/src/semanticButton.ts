import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { ToolbarButton } from '@jupyterlab/apputils';
import { writeNotebookWithLSP, saveFeedbackFile, 
  getNotebookCode, applyLSPFeedback, 
  removeWarningComments, splitCodeInLines,
  mergeLinesInString } from './fileManager'

import { API_ENDPOINT } from './config';

// ========== TOOLBAR BUTTON IMPLEMENTATION ==========
const buttonOnClick = async(panel: NotebookPanel): Promise<void> => {
  try {
    console.log('[Notebook Validation] Processing notebook');
    panel.context.save();

    // 1. PREPARE NOTEBOOK DATA
    console.log("[Notebook Validation] Preapring notebook data");
    const codeString = await getNotebookCode(panel);
    const codeLines = await splitCodeInLines(codeString);
    const cleanCodeLines = await removeWarningComments(codeLines);
    const cleanCodeString = await mergeLinesInString(cleanCodeLines);

    // 2. PREPARE JSON BODY
    console.log("[Notebook Validation] Preapring json body");
    const payload = {
        current_code: cleanCodeString
    };

    console.log("[Notebook Validation] Sending payload:");
    console.log(payload);

    // 3. SEND VALIDATION REQUEST
    console.log("[Notebook Validation] Sending validation request");
    const response = await fetch(`${API_ENDPOINT}/api/v1/feedback`, {
        method: 'POST',
        body: JSON.stringify(payload),  // Send as raw JSON string
        headers: {
            'Content-Type': 'application/json',  // Required header
            'Accept': 'application/json'
        },
        signal: AbortSignal.timeout(30000)  // 30s timeout
    });

    console.log("[Notebook Validation] Fetched response");
    // 4. HANDLE RESPONSE ERRORS
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
    console.log("[Notebook Validation] Response ok");

    // 5. PROCESS SUCCESSFUL RESPONSE
    const result = await response.json();  // Parse JSON response

    const resultText = result.non_localized_feedback;
    if (resultText === null) {
      throw new Error("md feedback lost");
    }
    const resultLSP = result.localized_feedback;
    if (resultText === null) {
      throw new Error("lsp feedback lost");
    }

    // 6. SAVE TO JUPYTERHUB FILE SYSTEM
    const savedFilePath = await saveFeedbackFile(panel.context.path, resultText);


    console.log(`Feedback saved to: ${savedFilePath}`);
    console.log("LSP:");
    console.log(resultLSP);

    // 7. REWRITE NOTEBOOK FILE 

    await writeNotebookWithLSP(panel, resultLSP);

  } catch (error) {
    // 8. HANDLE VALIDATION FAILURES
    console.error('[Notebook Validation] Validation failed:', error);

    let errorMessage = 'Request failed';
    if (error.name === 'AbortError') {
      errorMessage = 'Request timed out (30s)';
    } else if (error.message.includes('Failed to fetch')) {
      errorMessage = 'CORS error: Check server configuration';
    } else {
      errorMessage = error.message || 'Request failed';
    }

  } finally {

    // 9. RESET TO ORIGINAL STATE AFTER DELAY
    setTimeout(() => {
      // some future logic
    }, 3000);  // Reset after 3 seconds
  }

}
export const createToolbarButton = (panel: NotebookPanel) => {

  const button = new ToolbarButton({
    className: 'validation-toolbar-button',
    iconClass: 'jp-RefreshIcon',
    onClick: async () => {
      await buttonOnClick(panel);
    },
    tooltip: 'Validate notebook semantics'  // Initial tooltip
  });

  return button;
};