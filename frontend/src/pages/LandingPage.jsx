import { getGoogleAuthUrl } from "../api/client";

export default function LandingPage() {
  return (
    <div className="landing-page">
      <div className="landing-card">
        <h1>Email RAG Assistant</h1>
        <p>Answer questions strictly from your latest 100 Gmail emails.</p>
        <a className="connect-button" href={getGoogleAuthUrl()}>
          Connect Gmail
        </a>
      </div>
    </div>
  );
}
