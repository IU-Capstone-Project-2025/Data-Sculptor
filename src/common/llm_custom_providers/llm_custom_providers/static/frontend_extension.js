/* eslint-disable no-undef */
/**
 * Front-end extension that automatically augments Jupyter-AI chat messages with
 * the current notebook code.  It mimics the behaviour implemented on the
 * server side but provides a faster feedback-loop for the user because the
 * context is attached client-side before the request even hits the backend.
 */

define([
  'base/js/namespace',
  'jquery',
  'base/js/events',
], function (Jupyter, $, events) {
  'use strict';

  function getCurrentNotebookCode() {
    if (!Jupyter.notebook) return '';
    return Jupyter.notebook
      .get_cells()
      .filter((c) => c.cell_type === 'code')
      .map((c) => c.get_text())
      .filter((t) => t.trim() !== '')
      .join('\n\n');
  }

  function getActiveCellCode() {
    if (!Jupyter.notebook) return '';
    const cell = Jupyter.notebook.get_selected_cell();
    return cell && cell.cell_type === 'code' ? cell.get_text() : '';
  }

  function patchJupyterAI() {
    const interval = setInterval(() => {
      const chatWidget = document.querySelector('.jp-ai-chat-panel');
      if (!chatWidget) return;
      clearInterval(interval);

      const originalSend = window.jupyterAIChat?.sendMessage;
      if (!originalSend) return;

      window.jupyterAIChat.sendMessage = function (msg, opts = {}) {
        const enhanced = {
          ...opts,
          notebook_context: {
            current_code: getCurrentNotebookCode(),
            active_cell: getActiveCellCode(),
            notebook_path: Jupyter.notebook.notebook_path,
            notebook_name: Jupyter.notebook.notebook_name,
          },
        };
        return originalSend.call(this, msg, enhanced);
      };
    }, 1000);
  }

  function load_extension() {
    console.log('Loading Jupyter AI context extension…');
    if (Jupyter.notebook) patchJupyterAI();
    else events.on('notebook_loaded.Notebook', patchJupyterAI);
  }

  return {
    load_ipython_extension: load_extension,
    load_jupyter_extension: load_extension,
  };
}); 