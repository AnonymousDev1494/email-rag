import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="chat-input-bar">
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about your emails..."
        className="chat-input"
        disabled={disabled}
        rows={1}
      />
      <button type="button" onClick={submit} disabled={disabled || !text.trim()} className="send-button">
        Send
      </button>
    </div>
  );
}
