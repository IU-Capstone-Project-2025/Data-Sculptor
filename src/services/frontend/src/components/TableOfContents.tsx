import { Task } from "../utils/notebook";
import "./TableOfContents.css";
import checkIcon from "../assets/icons/check.svg";

interface TableOfContentsProps {
  tasks: Task[] | undefined;
  title: string | undefined;
  onCheck: () => void;
}

function TaskCell(props: TableOfContentsProps) {
  return (
    <div className="contents-list">
      <h3 className="content-link toc-title">
        <a href="#description">{props.title}</a>
        <button className="check-button" onClick={props.onCheck}>
          <img src={checkIcon} />
        </button>
      </h3>
      {props.tasks?.map((task) => (
        <a
          className="content-link"
          href={`#${task.description.task_id}`}
          key={task.description.task_id}
        >
          {task.description.title}
        </a>
      ))}
    </div>
  );
}

export default TaskCell;
