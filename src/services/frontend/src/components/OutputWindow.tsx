import "./OutputWindow.css";

interface OutputWindowProps {
  /** Optional output string to display */
  output?: string;
}

/**
 * Presentational component showing a scrollable panel with program output.
 * Hidden by default – parent decides when to render.
 */
export default function OutputWindow({ output }: OutputWindowProps) {
  return (
    <div className="output-window">
      {output ? (
        <pre>{output}</pre>
      ) : (
        <pre className="placeholder">Output will appear here...</pre>
      )}
    </div>
  );
} 