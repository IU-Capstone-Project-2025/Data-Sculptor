import { Notebook, NotebookCell } from "../types/notebook";

export interface Description {
  title: string;
  difficulty_level: string;
  rewards: string;
  task_statement: string;
  task_type: string;
  tools: string[];
}

export interface TaskDescription {
  title: string;
  task_id: string;
  state: string;
  issue: string;
  action: string;
  section_index: number;
}

export interface Task {
  description: TaskDescription;
  cells: NotebookCell[];
}

export function extractDescription(notebook: Notebook): Description {
  const firstCell = notebook.cells[0];
  const source = firstCell.source.join("");
  const data = JSON.parse(source);
  return {
    title: data.title || "Task",
    difficulty_level: data.difficulty_level || "Beginner",
    rewards: data.rewards || "",
    task_statement: data.task_statement || "",
    task_type: data.task_type || "Machine learning",
    tools: data.tools || ["Python"],
  };
}

export function extractTasks(notebook: Notebook): Task[] {
  function genID(): string {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      },
    );
  }

  function parseSeparator(cell: NotebookCell, index: number): TaskDescription {
    const source = cell.source.join("").trim();
    const lines = source.split("\n");
    const data = lines.slice(1, -1).join("");
    const task = JSON.parse(data);
    return {
      title: task.title || `Task ${result.length + 1}`,
      state: task.state || `State`,
      issue: task.issue || `Issue`,
      action: task.action || `Action`,
      task_id: genID(),
      section_index: index,
    };
  }

  function isSeparator(cell: NotebookCell): boolean {
    const source = cell.source.join("");
    const lines = source.split("\n");
    return lines[0].trim() === "```json";
  }

  const result: Task[] = [];
  let separator: NotebookCell | undefined = undefined;
  let cells: NotebookCell[] = [];
  function push() {
    if (!separator) {
      return;
    }
    // section_index equals current length of result before push
    result.push({ description: parseSeparator(separator, result.length), cells: cells });
    cells = [];
    separator = undefined;
  }
  for (const cell of notebook.cells.slice(1)) {
    if (isSeparator(cell)) {
      push();
      separator = cell;
    } else {
      cells.push(cell);
    }
  }
  push();
  return result;
}
