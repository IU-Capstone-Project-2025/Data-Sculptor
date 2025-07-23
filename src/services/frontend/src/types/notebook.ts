export interface NotebookCell {
  cell_type: "code" | "markdown";
  source: string[];
  metadata?: { [key: string]: any };
}

export interface Notebook {
  cells: NotebookCell[];
  metadata?: { [key: string]: any };
  nbformat: number;
  nbformat_minor: number;
}
