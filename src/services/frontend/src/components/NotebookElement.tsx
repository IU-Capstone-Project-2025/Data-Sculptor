import "./NotebookElement.css";
import { Notebook } from "../types/notebook";
import {
  Description,
  Task,
  extractDescription,
  extractTasks,
} from "../utils/notebook";
import DescriptionCell from "./DescriptionCell";
import Chat from "./Chat";
import TaskCell from "./TaskCell";
import TableOfContents from "./TableOfContents";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { store } from "../storage/store";
import { staticAnalysis, StaticDiagnostic } from "../utils/api";
import { useAppDispatch } from "../storage/hooks";
import { setCode } from "../storage/features/code";
interface NotebookElementProps {
  notebookUrl?: string;
  templateUrl?: string;
}

function NotebookElement(props: NotebookElementProps) {
  const [chatTask, setChatTask] = useState<Task | undefined>(undefined);
  const [description, setDescription] = useState<Description | undefined>(
    undefined,
  );
  const [tasks, setTasks] = useState<Task[] | undefined>(undefined);
  const [staticDiagnostics, setStaticDiagnostics] = useState<{
    [taskId: string]: StaticDiagnostic[];
  }>({});
  const params = useParams();

  const getNotebook = async () => {
    const url = props.notebookUrl || `/notebooks/${params.filename}.ipynb`;
    const response: Response = await fetch(url);
    const data: Notebook = await response.json();
    setDescription(extractDescription(data));
    const tasks = extractTasks(data);
    setTasks(tasks);
    return tasks;
  };

  function openChat(task: Task) {
    setChatTask(task);
  }

  function closeChat() {
    setChatTask(undefined);
  }

  const dispatch = useAppDispatch();

  const getTemplate = async (tasks: Task[]) => {
    const url =
      props.templateUrl || `/notebooks/${params.filename}_template.ipynb`;
    const response: Response = await fetch(url);
    const data: Notebook = await response.json();
    const cells = data.cells;
    const sources = cells.map((cell) => cell.source.join(""));
    for (let i = 0; tasks !== undefined && i < tasks.length; i++) {
      const task = tasks[i];
      const source = sources[i + 1];
      dispatch(setCode([task.description.task_id, source]));
    }
  };

  useEffect(() => {
    getNotebook().then(getTemplate);
  }, []);

  async function checkAll() {
    const state = store.getState();
    const diagnostics: { [taskId: string]: StaticDiagnostic[] } = {};
    const promises = [];
    for (const task of tasks ? tasks : []) {
      const taskId = task.description.task_id;
      const code = state.code.map[taskId];
      const promise = staticAnalysis(code).then(
        (d) => (diagnostics[taskId] = d),
      );
      promises.push(promise);
    }
    await Promise.all(promises);
    setStaticDiagnostics(diagnostics);
  }
  return (
    <div className="notebook">
      <div className="tasks-container">
        <div className="task-cells">
          <DescriptionCell description={description} />
          {tasks
            ? tasks.map((task) => (
                <TaskCell
                  task={task}
                  staticDiagnostics={
                    staticDiagnostics[task.description.task_id]
                      ? staticDiagnostics[task.description.task_id]
                      : []
                  }
                  key={task.description.task_id}
                  onChat={openChat}
                />
              ))
            : ""}
        </div>
        <div
          className={`table-of-contents ${chatTask !== undefined ? "chat" : ""}`}
        >
          {chatTask !== undefined ? (
            <Chat
              task={chatTask}
              onClose={closeChat}
              // TODO change user_id
              user_id="be147285-471a-4552-890b-3defccb1c9d3"
            />
          ) : (
            <TableOfContents
              tasks={tasks}
              title={description?.title}
              onCheck={checkAll}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default NotebookElement;
