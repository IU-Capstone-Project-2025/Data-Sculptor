import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import * as nbformat from '@jupyterlab/nbformat'; // Import nbformat for type definitions
import { ServerConnection } from '@jupyterlab/services';
import { PathExt, URLExt } from '@jupyterlab/coreutils';

// ========== NEW NOTEBOOK REWRITE FUNCTIONALITY ==========
export async function rewriteNotebook(panel: NotebookPanel): Promise<nbformat.INotebookContent> {
  const context = panel.context;
  const model = panel.content.model;

  if (!model) {
    throw new Error('No notebook model available');
  }

  try {
    // 1. Get current notebook content
    const current = model.toJSON() as nbformat.INotebookContent;
    
    // 2. Modify content (customize this transformation as needed)
    const modified = transformNotebookContent(current);
    
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

// Customize this function to implement your specific notebook modifications
export function transformNotebookContent(notebook: nbformat.INotebookContent): nbformat.INotebookContent {
  // Example transformation: Add timestamp cell at beginning
  const newCell: nbformat.ICodeCell = {
    cell_type: 'code',
    execution_count: null,
    metadata: {},
    outputs: [],
    source: [
      '# Modified by JupyterLab Extension\n',
      'from datetime import datetime\n',
      'print("Last modified:", datetime.now().isoformat())'
    ]
  };

  return {
    ...notebook,
    cells: [newCell, ...notebook.cells],
    metadata: {
      ...notebook.metadata,
      rewritten: true,
      modified_date: new Date().toISOString()
    }
  };
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
