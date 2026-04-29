# Gmail-Only BM25 Chat Assistant

Production-ready Gmail intelligence assistant with:
- FastAPI backend
- React + Vite frontend (ChatGPT-like interface)
- Google OAuth 2.0 + Gmail API
- SQLite email cache
- BM25 retrieval (`rank-bm25`) only
- OpenRouter free-tier model integration

This assistant is **strictly email-context only**. If not found in emails, it returns:

`Not found in your emails.`

## Project Structure

```text
backend/
  main.py
  requirements.txt
  .env.example
  auth/routes.py
  gmail/service.py
  rag/retriever.py
  rag/routes.py
  db/database.py
  db/models.py
  services/openrouter.py
  services/text_cleaning.py

frontend/
  package.json
  .env.example
  index.html
  vite.config.js
  src/
    main.jsx
    App.jsx
    styles.css
    api/client.js
    pages/LandingPage.jsx
    pages/ChatPage.jsx
    components/Sidebar.jsx
    components/ChatWindow.jsx
    components/MessageBubble.jsx
    components/ChatInput.jsx
```

## Backend Setup (Local)

1. Create virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create environment file:

```bash
cp .env.example .env
```

3. Fill backend `.env` values:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` (`http://localhost:8000/auth/callback`)
- `FRONTEND_URL` (`http://localhost:5173`)
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (free model, for example `deepseek/deepseek-r1-0528:free`)
- `DATABASE_PATH` (for example `./email_rag.db`)

4. Run backend:

```bash
uvicorn main:app --reload --port 8000
```

## Frontend Setup (Local)

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Create environment file:

```bash
cp .env.example .env
```

3. Set frontend `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

4. Run frontend:

```bash
npm run dev
```

Open `http://localhost:5173`.

## Google OAuth + Gmail API Setup

1. In Google Cloud Console:
- Create project
- Configure OAuth consent screen
- Enable **Gmail API**
- Create OAuth client (Web application)

2. Add Redirect URIs:
- `http://localhost:8000/auth/callback`
- `https://your-backend.onrender.com/auth/callback`

3. Copy OAuth client values into backend `.env`.

## How It Works

1. Click **Connect Gmail** on landing page.
2. Backend `/auth/google` redirects to Google OAuth.
3. `/auth/callback` exchanges token, stores token in SQLite, fetches last 100 emails, stores in `emails` table.
4. Chat message calls `POST /rag/query`.
5. Backend:
   - BM25 retrieves top 5 relevant emails
   - Builds strict prompt
   - Sends to OpenRouter
   - Returns model answer or exact fallback:
     `Not found in your emails.`

## API Endpoints

- `GET /health`
- `GET /auth/google`
- `GET /auth/callback`
- `POST /rag/query`

Example `POST /rag/query` body:

```json
{
  "question": "What did HR say about my leave approval?"
}
```

## Render Deployment (Backend)

1. Create a new Web Service on Render from this repo.
2. Root directory: `backend`
3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

5. Add environment variables from backend `.env`.
6. Set `GOOGLE_REDIRECT_URI` to:
   `https://your-backend.onrender.com/auth/callback`
7. Update Google Console redirect URIs accordingly.

Note: SQLite on free hosting is ephemeral; acceptable for free-tier MVP/demo.

## Vercel Deployment (Frontend)

1. Import repo in Vercel.
2. Set root directory to `frontend`.
3. Framework preset: Vite.
4. Set env var:

```env
VITE_API_BASE_URL=https://your-backend.onrender.com
```

5. Deploy and test OAuth connect + chat flow.

## Strict Answering Rules Implemented

- Uses only top retrieved emails as context
- No embeddings/vector DB
- Strict prompt with email-only policy
- Fallback on missing retrieval/LLM failure:
  `Not found in your emails.`
