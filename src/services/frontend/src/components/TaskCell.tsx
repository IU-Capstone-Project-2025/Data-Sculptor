import { useState } from "react";
import OutputWindow from "./OutputWindow";
import { Task } from "../utils/notebook";
import EditorElement from "./EditorElement";
import "./TaskCell.css";
import expandIcon from "../assets/icons/expand.svg";
import chatIcon from "../assets/icons/chat.svg";
import starIcon from "../assets/icons/star.svg";
import runIcon from "../assets/icons/run.svg";
import { StaticDiagnostic } from "../utils/api";
import { useAppSelector } from "../storage/hooks";

interface TaskCellProps {
  task: Task | null;
  staticDiagnostics: StaticDiagnostic[];
  onChat: (task: Task) => void;
}

interface TaskBodyProps {
  task: Task | null;
  staticDiagnostics: StaticDiagnostic[];
  onChat: (task: Task) => void;
}

function TaskBody(props: TaskBodyProps) {
  const feedback = useAppSelector((state) => {
    const task_id = props.task?.description.task_id;
    if (task_id === undefined) {
      return undefined;
    }
    return state.feedback.map[task_id];
  });
  const [cachedPressed, setCachedPressed] = useState<boolean>(false);
  const [showOutput, setShowOutput] = useState<boolean>(false);
  return (
    <>
      <div className="task-description">
        <div className="task-state">{props.task?.description.state}</div>
        <div className="task-issue">{props.task?.description.issue}</div>
      </div>
      <div className="code-editor">
        <div className="task-buttons">
          <button
            className="task-button task-button-run"
            onClick={() => setShowOutput(true)}
          >
            <img src={runIcon} />
          </button>
          <button
            className="task-button task-button-chat"
            onClick={() => {
              setCachedPressed(true);
              if (props.task !== null) {
                props.onChat(props.task);
              }
            }}
          >
            <img
              src={
                feedback === undefined && !cachedPressed ? starIcon : chatIcon
              }
            />
          </button>
        </div>
        {props.task ? (
          <EditorElement
            staticDiagnostics={props.staticDiagnostics}
            task_id={props.task?.description.task_id}
          />
        ) : undefined}
        {showOutput && <OutputWindow />}
      </div>
    </>
  );
}

function TaskCell(props: TaskCellProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="task-cell cell" id={props.task?.description.task_id}>
      <div
        className="task-title"
        onClick={(e) => {
          e.preventDefault();
          setCollapsed(!collapsed);
        }}
      >
        <h2>{props.task?.description.title}</h2>
        <img
          className={"task-expand-button" + (collapsed ? " collapsed" : "")}
          src={expandIcon}
          style={{ display: "none" }}
        />
      </div>
      {collapsed ? undefined : (
        <TaskBody
          staticDiagnostics={props.staticDiagnostics}
          task={props.task}
          onChat={props.onChat}
        />
      )}
    </div>
  );
}

export default TaskCell;
