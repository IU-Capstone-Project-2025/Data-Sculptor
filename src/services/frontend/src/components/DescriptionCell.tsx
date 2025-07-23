import { Description } from "../utils/notebook";
import expand from "../assets/icons/expand.svg";
import "./DescriptionCell.css";
import { useState } from "react";
import Markdown from "react-markdown";

interface DescriptionCellProps {
  description: Description | undefined;
}

function DescriptionBody(props: DescriptionCellProps) {
  return (
    <>
      <div className="description-difficulty-level">
        Difficulty: {props.description?.difficulty_level}
      </div>
      <div className="description-rewards">
        Rewards:
        <Markdown>{props.description?.rewards}</Markdown>
      </div>
      <div className="description-task-type">
        Task type: {props.description?.task_type}
      </div>
      <div className="description-task-statement">
        <Markdown>{props.description?.task_statement}</Markdown>
      </div>
      <div className="description-tools">
        Tools used:
        <ul className="description-tools-list">
          {props.description?.tools.map((tool, idx) => (
            <li key={idx}>{tool}</li>
          ))}
        </ul>
      </div>
    </>
  );
}

function DescriptionCell(props: DescriptionCellProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="description-cell cell" id="description">
      <div
        className="description-title"
        onClick={(e) => {
          e.preventDefault();
          setCollapsed(!collapsed);
        }}
      >
        <h2>{props.description?.title}</h2>
        <img
          className={
            "description-expand-button" + (collapsed ? " collapsed" : "")
          }
          src={expand}
          style={{ display: "none" }}
        />
      </div>
      {collapsed ? undefined : (
        <DescriptionBody description={props.description} />
      )}
    </div>
  );
}

export default DescriptionCell;
