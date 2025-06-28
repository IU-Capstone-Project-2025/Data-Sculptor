import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';


const CHECK_SVG = `
<svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <path fill="currentColor" d="M6.003 11.803L2.2 8l1.2-1.2 2.603 2.603L12.6 3.8l1.2 1.2z"/>
</svg>`;

const SPINNER_SVG = `
<svg viewBox="0 0 50 50" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25" cy="25" r="20" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
</svg>`;


// ========== PER-CELL BUTTON FUNCTIONALITY ==========
export const addCellButton = (cell: any, panel: NotebookPanel, seenCells: WeakSet<any>) => {
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
