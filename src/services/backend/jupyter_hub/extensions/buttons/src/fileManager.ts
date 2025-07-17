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
 
  // 2. Find first code cell
  const firstCodeCell = notebookContent.cells.find(cell => cell.cell_type === 'code');
  
  if (!firstCodeCell) {
    throw new Error('No code cell found in notebook');
  }

  console.log(firstCodeCell);
  let codeString = '';
 
  // Handle both string and array formats for cell source
  if (Array.isArray(firstCodeCell.source)) {
    codeString = firstCodeCell.source.join('\n');
  } else {
    codeString = firstCodeCell.source;
  }

  codeString = codeString.replace(/\\n/g, '\n')  // Replace double-escaped \\n with single \n
  console.log(codeString);
  return codeString;
}

export async function writeNotebookWithLSP(panel: NotebookPanel, lsp: any): Promise<nbformat.INotebookContent> {
  const context = panel.context;
  const model = panel.content.model;

  if (!model) {
    throw new Error('No notebook model available');
  }

  try {
    const notebookContent = await context.model.toJSON() as nbformat.INotebookContent;
    let codeString = await getNotebookCode(panel);

    let lines = codeString.split('\n');
    console.log(lines);
    const cleanedLines = await removeWarningComments(lines);
    console.log(cleanedLines);
    
    const transformedLines = await applyLSPFeedback(cleanedLines, lsp);
    console.log(transformedLines);
    
    const modifiedCode = transformedLines.join('\n');
    console.log(modifiedCode);
    
    // Find the first code cell index
    const firstCodeCellIndex = notebookContent.cells.findIndex(cell => cell.cell_type === 'code');
    
    if (firstCodeCellIndex === -1) {
      throw new Error('No code cell found in notebook');
    }
    
    const firstCodeCell = notebookContent.cells[firstCodeCellIndex];
    if (Array.isArray(firstCodeCell.source)) {
      firstCodeCell.source = modifiedCode.split('\n');
    } else {
      firstCodeCell.source = modifiedCode;
    }
    
    model.fromJSON(notebookContent);
    
    await context.save();
    
    console.log('Notebook rewritten and saved successfully!');
    return notebookContent;
  } catch (error) {
    console.error('Error rewriting notebook:', error);
    throw error;
  }
}

export async function mergeLinesInString(lines: string[]): Promise<string> {
  return lines.join('\n');
}

export async function splitCodeInLines(code: string): Promise<string[]> {
  return code.split('\n');
}

export async function removeWarningComments(lines: string[]): Promise<string[]> {
  const filteredLines = lines.map(line => line.replace(/# WARNING.*/g, ''));
  return filteredLines;
}

export async function applyLSPFeedback(lines: string[], lsp: any): Promise<string[]> {
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
export async function saveFeedbackFile(notebookPath: string, content: string, fileName?: string) {
  try {
    // Use provided fileName or fallback to timestamped name
    let finalFileName: string;
    if (fileName) {
      finalFileName = fileName;
    } else {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      finalFileName = `markdown_feedback_${timestamp}.md`;
    }
    const directory = PathExt.dirname(notebookPath);
    const filePath = PathExt.join(directory, finalFileName);

    // Get server settings with authentication
    const serverSettings = ServerConnection.makeSettings();
    const url = URLExt.join(serverSettings.baseUrl, 'api/contents', filePath);

    // Prepare request model
    const model = {
      type: 'file',
      format: 'text',
      content: content
    };

    // Send PUT request (will overwrite if file exists)
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
