import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import * as nbformat from '@jupyterlab/nbformat'; // Import nbformat for type definitions
import { ServerConnection } from '@jupyterlab/services';
import { PathExt, URLExt } from '@jupyterlab/coreutils';

// ========== NEW NOTEBOOK REWRITE FUNCTIONALITY ==========
// rewriteNotebook adds lsp comments
export async function rewriteNotebook(panel: NotebookPanel, lsp: any): Promise<nbformat.INotebookContent> {
  const context = panel.context;
  const model = panel.content.model;

  if (!model) {
    throw new Error('No notebook model available');
  }

  try {
    // 1. Get current notebook content
    const current = model.toJSON() as nbformat.INotebookContent;
    
    // 2. Modify content (customize this transformation as needed)
    const notebookString = JSON.stringify(current, null, 2);
    const lines = notebookString.split('\n');
    
    // 3. Apply your transformation logic to the lines array
    const transformedLines = applyLSPFeedback(lines, lsp);  // Implement your logic here
    
    // 4. Join back into a single string
    const modifiedString = transformedLines.join('\n');
    
    // 5. Parse back to notebook content
    const modified = JSON.parse(modifiedString) as nbformat.INotebookContent;
    
    // 3. Update model with modified content
    model.fromJSON(modified);
    
    // 4. Save to disk
    await context.save();
    
    console.log('Notebook rewritten and saved successfully!');
    return modified;
  } catch (error) {
    console.error('Error rewriting notebook:', error);
    throw error;
  }
}

// Apply LSP feedback to specific lines
function applyLSPFeedback(lines: string[], lsp: any): string[] {
  // Create a copy of the lines array
  const newLines = [...lines];
  
  // Process each feedback entry
  for (const feedback of lsp) {
    const lineNum = feedback.range.start.line;
    
    // Validate line number
    if (lineNum >= 0 && lineNum < newLines.length) {
      // Append message to the end of the line
      newLines[lineNum] = newLines[lineNum] + ' # WARNING: ' + feedback.message;
    } else {
      console.warn(`Invalid line number ${lineNum} in LSP feedback`);
    }
  }
  
  return newLines;
}

// 2. FILE SAVER FUNCTION
export async function saveFeedbackFile(notebookPath: string, content: string) {
    try {
        // Create filename with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fileName = `markdown_feedback_${timestamp}.md`;
        const directory = PathExt.dirname(notebookPath);
        const filePath = PathExt.join(directory, fileName);

        // Get server settings with authentication
        const serverSettings = ServerConnection.makeSettings();
        const url = URLExt.join(serverSettings.baseUrl, 'api/contents', filePath);

        // Prepare request model
        const model = {
            type: 'file',
            format: 'text',
            content: content
        };

        // Send PUT request
        const response = await ServerConnection.makeRequest(url, {
            method: 'PUT',
            body: JSON.stringify(model),
            headers: {
                'Content-Type': 'application/json',
                ...(serverSettings.token ? { Authorization: `Token ${serverSettings.token}` } : {})
            }
        }, serverSettings);

        // Handle response
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Failed to save file: ${response.status} - ${errorData.message || response.statusText}`);
        }

        console.log(`Successfully saved feedback to: ${filePath}`);
        return filePath;

    } catch (error) {
        console.error('File save error:', error);
        throw error;
    }
}
