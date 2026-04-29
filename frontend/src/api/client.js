import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export function getGoogleAuthUrl() {
  return `${API_BASE_URL}/auth/google`;
}

export async function queryRag(question, sessionId) {
  const response = await api.post("/rag/query", { question, session_id: sessionId });
  return response.data;
}

export async function getHealth() {
  const response = await api.get("/health");
  return response.data;
}

export async function syncEmails() {
  const response = await api.post("/emails/sync");
  return response.data;
}
