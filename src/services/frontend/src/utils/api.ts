type Severity = "hint" | "info" | "warning" | "error";
export function severityFromNumber(severity: number): Severity {
  switch (severity) {
    case 1:
      return "error";
    case 2:
      return "warning";
    case 3:
      return "info";
    default:
      return "hint";
  }
}

export interface StaticDiagnostic {
  tool: string;
  type: Severity;
  module: string;
  obj: string;
  line: number;
  column: number;
  endLine: number;
  endColumn: number;
  symbol: string;
  message: string;
  "message-id": string;
  severity: number;
}

export async function staticAnalysis(
  code: string,
): Promise<StaticDiagnostic[]> {
  // TODO anti-jitter
  if (code === "") {
    return [];
  }
  const blob = new Blob([code], { type: "text/x-python" });
  const file = new File([blob], "fib.py", { type: "text/x-python" });
  const formData = new FormData();
  formData.append("code_file", file);
  const response = await fetch("http://jh.data-sculptor.ru:52766/analyze", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    return [];
  }
  const body: { diagnostics: StaticDiagnostic[] } = await response.json();
  return body["diagnostics"];
}

interface RealTimeDiagnostics {
  source: string;
  range: {
    start: {
      line: number;
      character: number;
    };
    end: {
      line: number;
      character: number;
    };
  };
  message: string;
  severity: number;
}

// Track if real-time analysis is working to avoid repeated timeouts
let realTimeAnalysisDisabled = false;
let lastFailureTime = 0;
const RETRY_DELAY = 60000; // 1 minute before retrying

export async function realTimeAnalysis(
  code: string,
): Promise<RealTimeDiagnostics[]> {
  if (code === "") {
    return [];
  }
  
  
  try {
    const blob = new Blob([code], { type: "text/x-python" });
    const file = new File([blob], "fib.py", { type: "text/x-python" });
    const formData = new FormData();
    formData.append("file", file);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    
    const response = await fetch("http://jh.data-sculptor.ru:52767/analyze", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    
    const body: { diagnostics: RealTimeDiagnostics[] } = await response.json();
    
    
    return body["diagnostics"];
  } catch (error) {
    return [];
  }
}

interface ChatRequest {
  conversation_id: string; // Conversation identifier, UUID.
  user_id: string; // User identifier, UUID or similar.
  message: string; // User's current message/question.
  current_code: string; // Code snippet to analyse.
  cell_code_offset?: number; // Global line offset inside the notebook.
  current_non_localized_feedback?: string; // Existing high-level feedback for the code.
  current_localized_feedback?: LocalizedWarning[]; // Existing line-localized warnings.
  use_deep_analysis?: boolean; // Whether to use deep analysis for the response.
}

interface ChatResponse {
  message: string; // Response message.
}

interface LocalizedWarning {
  range: Range;
  severity?: 2; // Default: 2
  code?: "custom-warning"; // Default: "custom-warning"
  source?: "Data Sculptor"; // Default: "Data Sculptor"
  message: string;
}

interface Position {
  line: number; // Zero-based line index.
  character?: number; // Zero-based character offset.
}

interface Range {
  start: Position;
  end: Position;
}

export async function sendMessage(
  message: string,
  localized_feedback: LocalizedWarning[],
  feedback: string,
  conversation_id: string,
  user_id: string,
  code: string,
): Promise<string> {
  const request: ChatRequest = {
    conversation_id: conversation_id,
    user_id: user_id,
    message: message,
    current_code: code || "",
    current_localized_feedback: localized_feedback,
    current_non_localized_feedback: feedback,
  };
  const response = await fetch("http://jh.data-sculptor.ru:52235/api/v1/chat", {
    method: "POST",
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    return "Could not get the response from LLM";
  }
  const data: ChatResponse = await response.json();
  return data.message;
}

export interface Feedback {
  non_localized_feedback: string;
  localized_feedback: LocalizedWarning[];
}

export async function semanticFeedback(
  code: string,
  section_index: number,
): Promise<Feedback> {
  const fillerFeedback = {
    non_localized_feedback: "I've highlighted issues directly in the code; no additional summary was provided.",
    localized_feedback: [],
  };
  if (code === "") {
    return fillerFeedback;
  }
  const requestBody = {
    current_code: code,
    cell_code_offset: 0,
    section_index: section_index,
    case_id: "2e70294e-4491-4301-b2cf-13219676f38e",
    use_deep_analysis: false,
  };
  const response = await fetch(
    "http://jh.data-sculptor.ru:52234/api/v1/feedback",
    {
      method: "POST",
      body: JSON.stringify(requestBody),
      headers: { "Content-Type": "application/json" },
    },
  );
  if (!response.ok) {
    return fillerFeedback;
  }
  const result: Feedback = await response.json();
  if (result.non_localized_feedback === "") {
    result.non_localized_feedback = fillerFeedback.non_localized_feedback;
  }
  if (result.localized_feedback.length == 0) {
    result.localized_feedback = fillerFeedback.localized_feedback;
  }
  return result;
}
