export default function Sidebar({ chats, onNewChat, onSync, syncing, health }) {
  return (
    <aside className="sidebar">
      <div>
        <h1 className="app-title">Email RAG Assistant</h1>
        <button type="button" className="new-chat-button" onClick={onNewChat}>
          New Chat
        </button>
        <button type="button" className="sync-button" onClick={onSync} disabled={syncing}>
          {syncing ? "Syncing..." : "Refresh Emails"}
        </button>
        <p className="status-line">
          {health?.connected ? `Connected | Cached: ${health?.emails_cached ?? 0}` : "Not connected"}
        </p>
      </div>
      <div className="chat-history">
        {chats.length === 0 ? (
          <p className="history-empty">No chats yet</p>
        ) : (
          chats.map((chat, idx) => (
            <div className="history-item" key={`${chat}-${idx}`}>
              {chat}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
