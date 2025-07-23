import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { monokai } from "@uiw/codemirror-theme-monokai";
import { useCallback } from "react";
import { setCode } from "../storage/features/code";
import { useAppDispatch, useAppSelector } from "../storage/hooks";
import { linter, lintGutter } from "@codemirror/lint";
import "./EditorElement.css";
import {
  Feedback,
  realTimeAnalysis,
  severityFromNumber,
  StaticDiagnostic,
} from "../utils/api";

interface EditorProps {
  staticDiagnostics: StaticDiagnostic[];
  task_id: string;
}

function convert(text: string, line: number, col: number): number {
  // TODO rewrite AI slop
  const lines = text.split("\n");
  if (line > lines.length) {
    return 0;
  }
  const lineText = lines[line];
  if (col > lineText.length) {
    return 0;
  }
  let index = 0;
  for (let i = 0; i < line; i++) {
    index += lines[i].length + 1;
  }
  index += col;
  return index;
}

const realTimeLint = linter(async (view) => {
  const code: string = view.state.doc.toString();
  const diagnostics = await realTimeAnalysis(code);

  return diagnostics.map((d) => {
    return {
      from: convert(code, d.range.start.line, d.range.start.character),
      to: convert(code, d.range.end.line, d.range.end.character),
      severity: severityFromNumber(d.severity),
      message: d.message,
    };
  });
});

function EditorElement(props: EditorProps) {
  const code = useAppSelector((state) => state.code.map[props.task_id]);
  const dispatch = useAppDispatch();
  const onChange = useCallback(
    (newCode: string) => {
      dispatch(setCode([props.task_id, newCode]));
    },
    [props.task_id, dispatch],
  );
  const staticLint = linter(async (view) => {
    const code: string = view.state.doc.toString();
    const diagnostics = props.staticDiagnostics;

    return diagnostics.map((d) => {
      return {
        from: convert(code, d.line, d.column),
        to: convert(code, d.endLine, d.endColumn),
        severity: d.type,
        message: d.message,
      };
    });
  });

  const feedback: Feedback | undefined = useAppSelector(
    (state) => state.feedback.map[props.task_id],
  );

  const semanticLint = linter(async (view) => {
    const code: string = view.state.doc.toString();
    const diagnostics = feedback ? feedback.localized_feedback : [];

    return diagnostics.map((d) => {
      return {
        from: convert(
          code,
          d.range.start.line,
          d.range.start.character ? d.range.start.character : 0,
        ),
        to: convert(
          code,
          d.range.end.line,
          d.range.end.character ? d.range.end.character : 0,
        ),
        severity: severityFromNumber(d.severity ? d.severity : 2),
        message: d.message,
      };
    });
  });

  return (
    <CodeMirror
      extensions={[
        python(),
        lintGutter(),
        realTimeLint,
        staticLint,
        semanticLint,
      ]}
      theme={monokai}
      value={code}
      onChange={onChange}
    />
  );
}

export default EditorElement;
