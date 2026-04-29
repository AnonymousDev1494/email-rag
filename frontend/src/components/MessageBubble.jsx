export default function MessageBubble({ role, content, sources = [] }) {
  return (
    <div className={`message-row ${role === "user" ? "user-row" : "assistant-row"}`}>
      <div className={`message-bubble ${role === "user" ? "user-bubble" : "assistant-bubble"}`}>
        {content}
        {role === "assistant" && sources.length > 0 && (
          <div className="sources-wrap">
            <div className="sources-title">Sources used</div>
            {sources.map((source) => (
              <div key={source.id || `${source.subject}-${source.date}`} className="source-item">
                <div className="source-subject">{source.subject || "No subject"}</div>
                <div className="source-meta">
                  {source.sender || "Unknown sender"} | {source.date || "Unknown date"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
