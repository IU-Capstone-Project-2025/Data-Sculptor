import { useCallback, useEffect, useState } from "react";
import "./Chat.css";
import { Task } from "../utils/notebook";
import backIcon from "../assets/icons/back.svg";
import sendIcon from "../assets/icons/send.svg";
import starIcon from "../assets/icons/star.svg";
import { Feedback, semanticFeedback, sendMessage } from "../utils/api";
import { useAppDispatch, useAppSelector } from "../storage/hooks";
import { setFeedback } from "../storage/features/feedback";
import Markdown from "react-markdown";

interface ChatProps {
  task: Task;
  user_id: string;
  onClose: () => void;
}

function Chat(props: ChatProps) {
  const [messages, setMessages] = useState<
    Array<{ sender: string; text: string }>
  >([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [gettingFeedback, setGettingFeedback] = useState(false);

  const code: string | undefined = useAppSelector(
    (state) => state.code.map[props.task.description.task_id],
  );

  const storedFeedback = useAppSelector(
    (state) => state.feedback.map[props.task.description.task_id],
  );

  useEffect(() => {
    // When the selected task changes, seed chat with any stored AI feedback
    const initialMsgs: Array<{ sender: string; text: string }> = [];
    if (storedFeedback && storedFeedback.non_localized_feedback !== "") {
      initialMsgs.push({ sender: "ai", text: storedFeedback.non_localized_feedback });
    }
    setMessages(initialMsgs);
    setInputValue("");
    setIsLoading(false);
  }, [props.task.description.task_id]);
  const dispatch = useAppDispatch();
  const updateFeedback = useCallback(
    (newFeedback: Feedback, task_id: string) => {
      dispatch(setFeedback([task_id, newFeedback]));
    },
    [dispatch],
  );
  const getFeedback = useCallback(async () => {
    if (gettingFeedback) {
      return;
    }
    setGettingFeedback(true);
    try {
      const f = await semanticFeedback(code || "", props.task.description.section_index);
      updateFeedback(f, props.task.description.task_id);
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: f.non_localized_feedback },
      ]);
    } catch (error) {
      console.error("Failed to get semantic feedback:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Sorry, I couldn't analyze your code right now. Please try again." },
      ]);
    } finally {
      setGettingFeedback(false);
    }
  }, [gettingFeedback, code, updateFeedback, props.task.description.task_id]);

  const handleSendMessage = () => {
    if (inputValue.trim() === "" || isLoading) return;
    const userMessage = { sender: "user", text: inputValue };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setTimeout(async () => {
      const message = await sendMessage(
        inputValue,
        [
          {
            range: {
              start: { line: 0, character: 0 },
              end: { line: 0, character: 0 },
            },
            message: "Mock localized feedback",
          },
        ],
        "Feedback",
        props.task.description.task_id,
        props.user_id,
        code,
      );
      const aiResponse = { sender: "ai", text: message };
      setMessages((prev) => [...prev, aiResponse]);
      setIsLoading(false);
    }, 500);
  };
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      handleSendMessage();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-title-container">
        <button className="chat-back-button" onClick={props.onClose}>
          <img src={backIcon} />
        </button>
        <div className="chat-title">
          <h3>{props.task.description.title}</h3>
        </div>
      </div>
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            <Markdown>{msg.text}</Markdown>
          </div>
        ))}
        {isLoading && <div className="message ai loading">Thinking...</div>}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={isLoading}
          style={{ outline: 0 }}
        />
        <div className="input-controls">
          <button
            className="send-button"
            onClick={getFeedback}
            disabled={gettingFeedback}
          >
            <img src={starIcon} />
          </button>
          <button
            onClick={handleSendMessage}
            disabled={isLoading || inputValue.trim() === ""}
            className="send-button"
          >
            <img src={sendIcon} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default Chat;
