import ChatPage from "./pages/ChatPage";
import LandingPage from "./pages/LandingPage";

export default function App() {
  const path = window.location.pathname;
  if (path === "/chat") {
    return <ChatPage />;
  }
  return <LandingPage />;
}
