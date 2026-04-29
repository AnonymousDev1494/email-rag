import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({ messages, loading }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="chat-window">
      {messages.map((message, idx) => (
        <MessageBubble
          key={`${message.role}-${idx}`}
          role={message.role}
          content={message.content}
          sources={message.sources || []}
        />
      ))}
      {loading && <MessageBubble role="assistant" content="Thinking..." />}
      <div ref={endRef} />
    </div>
  );
}
