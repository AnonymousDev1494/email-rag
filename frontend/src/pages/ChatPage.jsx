import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import { getHealth, queryRag, syncEmails } from "../api/client";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [history, setHistory] = useState([]);
  const [health, setHealth] = useState({ connected: false, emails_cached: 0 });
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`);

  const lastUserQuestions = useMemo(
    () => messages.filter((m) => m.role === "user").map((m) => m.content).slice(-10).reverse(),
    [messages]
  );

  const onNewChat = () => {
    if (messages.length > 0) {
      const userMessages = messages.filter((msg) => msg.role === "user");
      const lastPrompt = userMessages[userMessages.length - 1]?.content;
      if (lastPrompt) {
        setHistory((prev) => [lastPrompt, ...prev].slice(0, 20));
      }
    }
    setMessages([]);
    setSessionId(`session-${Date.now()}`);
  };

  const refreshHealth = async () => {
    try {
      const data = await getHealth();
      setHealth({
        connected: !!data?.connected,
        emails_cached: Number(data?.emails_cached || 0),
      });
    } catch (_error) {
      setHealth({ connected: false, emails_cached: 0 });
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  const onSync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await syncEmails();
      await refreshHealth();
    } catch (_error) {
      // Keep UI minimal; status remains visible via health.
    } finally {
      setSyncing(false);
    }
  };

  const onSend = async (question) => {
    if (loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const data = await queryRag(question, sessionId);
      const answer = data?.answer || "Not found in your emails.";
      const sources = Array.isArray(data?.sources) ? data.sources : [];
      setMessages((prev) => [...prev, { role: "assistant", content: answer, sources }]);
    } catch (_error) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Not found in your emails." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-layout">
      <Sidebar
        chats={[...history, ...lastUserQuestions].slice(0, 20)}
        onNewChat={onNewChat}
        onSync={onSync}
        syncing={syncing}
        health={health}
      />
      <main className="chat-main">
        <ChatWindow messages={messages} loading={loading} />
        <ChatInput onSend={onSend} disabled={loading} />
      </main>
    </div>
  );
}
