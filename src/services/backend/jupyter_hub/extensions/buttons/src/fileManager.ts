import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import * as nbformat from '@jupyterlab/nbformat'; // Import nbformat for type definitions
import { ServerConnection } from '@jupyterlab/services';
import { PathExt, URLExt } from '@jupyterlab/coreutils';

// ========== NEW NOTEBOOK REWRITE FUNCTIONALITY ==========
// rewriteNotebook adds lsp comments
export async function getNotebookCode(panel: NotebookPanel): Promise<any> {
  const context = panel.context;
  // 1. Get current notebook content with proper typing
  const notebookContent = await context.model.toJSON() as nbformat.INotebookContent;
 
  // 2. Get first cell content
  if (notebookContent.cells.length === 0 || notebookContent.cells[0].cell_type !== 'code') {
    throw new Error('First cell is not a code cell');
  }

  const firstCell = notebookContent.cells[0];
  console.log(firstCell);
  let codeString = '';
 
  // Handle both string and array formats for cell source
  if (Array.isArray(firstCell.source)) {
    codeString = firstCell.source.join('\n');
  } else {
    codeString = firstCell.source;
  }

  codeString = codeString.replace(/\\n/g, '\n')  // Replace double-escaped \\n with single \n
  console.log(codeString);
  return codeString;
}

export async function rewriteNotebook(panel: NotebookPanel, lsp: any): Promise<nbformat.INotebookContent> {
  const context = panel.context;
  const model = panel.content.model;

  if (!model) {
    throw new Error('No notebook model available');
  }

  try {
    // 1. Get current notebook content with proper typing
    const notebookContent = await context.model.toJSON() as nbformat.INotebookContent;
    let codeString = await getNotebookCode(panel);

    // 3. Remove existing warning comments
    const cleanedCode = removeWarningComments(codeString);
    console.log(cleanedCode);
    let lines = cleanedCode.split('\n');
    console.log(lines);
    
    // 4. Apply LSP feedback to lines
    const transformedLines = applyLSPFeedback(lines, lsp);
    console.log(transformedLines);
    
    // 5. Join back into a single string
    const modifiedCode = transformedLines.join('\n');
    console.log(modifiedCode);
    
    const firstCell = notebookContent.cells[0];
    // 6. Update the first cell content (preserve original format)
    if (Array.isArray(firstCell.source)) {
      firstCell.source = modifiedCode.split('\n');
    } else {
      firstCell.source = modifiedCode;
    }
    
    // 7. Update model with modified content
    model.fromJSON(notebookContent);
    
    // 8. Save to disk
    await context.save();
    
    console.log('Notebook rewritten and saved successfully!');
    return notebookContent;
  } catch (error) {
    console.error('Error rewriting notebook:', error);
    throw error;
  }
}

function removeWarningComments(code: string): string {
  const lines = code.split('\n');
  const filteredLines = lines.filter(line => !line.trim().startsWith('# WARNING: '));
  return filteredLines.join('\n');
}

function applyLSPFeedback(lines: string[], lsp: any): string[] {
  // Create a copy of the lines array
  const newLines = [...lines];
  
  // Process each feedback entry
  for (const feedback of lsp) {
    // Validate feedback structure
    if (!feedback?.range?.start || typeof feedback.range.start.line !== 'number') {
      console.warn('Invalid feedback entry', feedback);
      continue;
    }
    
    const lineNum = feedback.range.start.line;
    
    // Validate line number
    if (lineNum >= 0 && lineNum < newLines.length) {
      // Append message to the end of the line as Python comment
      newLines[lineNum] = newLines[lineNum] + '  # WARNING: ' + feedback.message;
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
