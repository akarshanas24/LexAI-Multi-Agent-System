# ⚖️ LexAI — AI-Powered Multi-Agent Legal Reasoning Platform

LexAI is an intelligent legal assistance platform that leverages **Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and AI agents** to analyze legal cases, simulate multi-agent legal debates, and provide verdict predictions with detailed reasoning from multiple perspectives.

The platform combines AI-driven reasoning with efficient document retrieval, enabling users to explore legal scenarios, understand complex cases, and obtain context-aware legal insights through structured multi-agent collaboration.

**Version:** 2.0.0 | **Status:** Production-Ready

---

## 🚀 Core Features

### 📄 Legal Case & Document Analysis
- Upload and analyze detailed legal cases and documents
- Extract meaningful information from complex legal content
- Generate structured insights with semantic understanding
- Support for case history and audit trails

### 🤖 Multi-Agent Legal Reasoning
- **5 Specialized AI Agents** working in coordination:
  - **Research Agent** — Retrieves relevant legal precedents and documents
  - **Defense Agent** — Constructs counter-arguments and mitigating factors
  - **Prosecution Agent** — Builds evidence-based accusations
  - **Judge Agent** — Evaluates both sides and renders impartial verdicts
  - **Appeals Agent** — Reviews verdicts for procedural and substantive errors
- Simulates realistic legal debate from multiple perspectives
- Provides reasoning behind predicted outcomes

### 🔍 Retrieval-Augmented Generation (RAG)
- Semantic search over legal document knowledge base
- Context-aware information retrieval for enhanced accuracy
- Embedding-based document similarity matching
- Improves reliability and relevance of AI-generated insights

### 🧠 LLM-Powered Insights
- Integrates Claude 3.5 or Ollama for intelligent reasoning
- Generates human-like legal explanations and arguments
- Context-aware responses based on retrieved information
- Fallback system ensures availability

### 🔐 Secure User Management
- JWT-based authentication with 8-hour session expiry
- Bcrypt password hashing for secure storage
- Protected API endpoints with user isolation
- Activity logging and audit trails

### 📊 Additional Capabilities
- Rate limiting (10 requests/minute per IP)
- PDF export of case summaries with verdicts
- Real-time streaming response display
- Customizable reasoning profiles (balanced, strict, lenient)
- Interactive knowledge base management

---

## 🏗️ System Architecture

```
                User Browser
                     |
                     ↓
        Web Application (HTML/JS/CSS)
                     |
                     ↓
              FastAPI Backend
                     |
        --------------------------------
        |                              |
        ↓                              ↓
Document Processing          AI Reasoning Engine
        |                              |
        ↓                              ↓
Vector Retrieval           AgentOrchestrator
        |                              |
        ↓                    ┌─────────┼─────────┐
     FAISS/                  ↓         ↓         ↓
  Embeddings          Research   Defense   Prosecution
        |                              |         ↓
        └──────────── RAG Pipeline ────┼─── Judge ──→ Appeals
                           |           ↓
                           ↓
                    LLM Backend
                    (Ollama)
                           |
                           ↓
              Legal Analysis & Verdict
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML, CSS, JavaScript | User interface & interaction |
| **Backend** | Python, FastAPI, Uvicorn | RESTful API & server |
| **Database** | SQLite, SQLAlchemy | Case storage & ORM |
| **AI/NLP** | Claude 3.5 Sonnet / Ollama | LLM inference |
| **RAG** | FAISS, Sentence Transformers | Vector search & embeddings |
| **Auth** | Python-Jose, Passlib | JWT authentication |
| **Rate Limiting** | SlowAPI | Request throttling |
| **Logging** | Loguru | Structured logging |
| **PDF Export** | ReportLab | Document generation |
| **Testing** | Pytest, HTTPx | Unit & integration tests |

---

## 🔄 How It Works

1. **User Input** — User submits a legal case description or uploads documents
2. **Document Processing** — System extracts and processes legal information
3. **Vector Retrieval** — Semantic search retrieves relevant legal documents from knowledge base
4. **Agent Analysis** — 5 specialized agents analyze the case:
   - Research Agent gathers precedents
   - Defense/Prosecution agents build respective arguments
   - Judge agent evaluates both sides
   - Appeals agent reviews for errors (optional)
5. **LLM Reasoning** — Claude or Ollama generates detailed legal reasoning
6. **Verdict Generation** — System produces a verdict with explanations
7. **Result Display** — Results streamed to frontend in real-time

---

## 📥 Installation & Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/multi_debate_system.git
cd multi_debate_system
```

### Step 2: Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create `.env` file in project root:
```env
# LLM Backend (choose one)
ANTHROPIC_API_KEY=sk-ant-xxxxx              # For Claude API
OLLAMA_ENABLED=true                         # For Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434     # Ollama endpoint

# Database & Security
DATABASE_URL=sqlite+aiosqlite:///./lexai_runtime.db
SECRET_KEY=your-secret-key-change-me        # Generate: openssl rand -hex 32

# Server
HOST=127.0.0.1
PORT=8000
DEBUG=true
```

### Step 5: Run Backend Server
```bash
uvicorn main:app --reload --port 8000
```

**Access Points:**
- Frontend: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 📋 API Endpoints

### Case Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/cases/analyze` | Analyze legal case with all agents |
| GET | `/api/cases` | List user's cases |
| GET | `/api/cases/{case_id}` | Get case details |
| DELETE | `/api/cases/{case_id}` | Delete case |
| POST | `/api/cases/{case_id}/export-pdf` | Export case as PDF |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user account |
| POST | `/auth/login` | Authenticate and get JWT token |
| POST | `/auth/reset-password` | Reset forgotten password |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/backend-info` | Show LLM backend info |
| GET | `/api/settings` | Get runtime configuration |
| PUT | `/api/settings` | Update runtime settings |

---

## ⚙️ Configuration

Runtime settings in `config/runtime_settings.json`:
```json
{
  "default_include_appeals": false,
  "retrieval_documents": 4,
  "reasoning_profile": "balanced",
  "evidence_highlight_limit": 8,
  "typing_speed_ms": 8,
  "auto_scroll_results": true
}
```

**LLM Selection Priority:**
1. Ollama (if enabled and running)
2. Anthropic Claude (if API key set)
3. Fallback (local responses)

## 🧪 Testing & Quality Assurance

### Run Tests
```bash
# Run all tests
pytest

# With coverage report
pytest --cov=agents --cov=api --cov=auth --cov=db

# Specific test file
pytest test_agents.py -v
```

### Test Files
- `test_agents.py` — Agent reasoning and orchestration
- `test_auth.py` — User authentication and JWT tokens
- `test_cases.py` — Case CRUD operations
- `test_dashboard.py` — Frontend integration tests

Tests use in-memory SQLite database isolated from production data.

---

## 📁 Project Structure

```
multi_debate_system/
│
├── main.py                          # FastAPI application entry point
│
├── agents/                          # AI Agent implementations
│   ├── base_agent.py               # Base agent class with LLM logic
│   ├── orchestrator.py             # Multi-agent orchestration
│   ├── research_agent.py           # Document retrieval
│   ├── defense_agent.py            # Defense arguments
│   ├── prosecution_agent.py        # Prosecution arguments
│   ├── judge_agent.py              # Verdict rendering
│   └── appeals_agent.py            # Appeals review
│
├── api/                             # RESTful API
│   └── routes.py                   # All API endpoints
│
├── auth/                            # Authentication
│   ├── auth.py                     # JWT & password utilities
│   └── routes.py                   # Auth endpoints
│
├── db/                              # Database layer
│   ├── database.py                 # SQLAlchemy setup
│   ├── models.py                   # ORM models
│   └── crud.py                     # CRUD operations
│
├── rag/                             # RAG system
│   ├── knowledge_base.py           # Semantic search
│   └── legal_corpus.json           # Legal documents
│
├── config/                          # Configuration
│   ├── settings.py                 # Environment settings
│   └── runtime_settings.json       # Runtime config
│
├── middleware/                      # ASGI middleware
│   ├── logging_middleware.py       # Request logging
│   └── rate_limit.py               # Rate limiting
│
├── utils/                           # Utilities
│   ├── logger.py                   # Loguru setup
│   └── fallback_reasoning.py       # Fallback responses
│
├── Frontend Files
│   ├── index.html                  # Main UI template
│   ├── style.css                   # Styling
│   ├── app.js                      # State management
│   ├── ui.js                       # UI components
│   └── api.js                      # API client
│
├── logs/                            # Application logs
├── requirements.txt                 # Python dependencies
├── conftest.py                      # Pytest configuration
└── README.md                        # Documentation
```

---

## 🎯 Key Highlights

✨ **What Makes LexAI Stand Out:**

- **Multi-Agent Coordination** — First-of-its-kind approach to legal reasoning with 5 synchronized agents
- **RAG Integration** — Context-aware legal document retrieval for accurate reasoning
- **Production-Ready** — Fully tested, logged, and rate-limited for real-world deployment
- **Flexible Backend** — Works with Claude API, open-source Ollama, or fallback mode
- **Secure by Design** — JWT authentication, password hashing, activity auditing
- **Real-time Streaming** — Live response display with WebSocket support
- **PDF Export** — Generate professional case summaries with verdicts
- **Scalable Architecture** — Async FastAPI for high-throughput handling
- **Well-Tested** — Comprehensive test suite with pytest and coverage reports
- **Extensively Documented** — Clear API docs, inline comments, and examples


---

## 💡 Use Cases

- **Legal Firms** — Accelerate case preparation and legal research
- **Law Students** — Learn legal reasoning from AI-generated arguments
- **Paralegals** — Assist with document analysis and case summaries
- **Corporate Legal Teams** — Internal contract review and risk assessment
- **Judiciary Support** — Reference research for judicial decisions
- **Legal Technology** — Build on LexAI's foundation for specialized applications

---

## 👨‍💻 Author & Credits

**Developed by:** AI-Powered Legal Reasoning Team  
**LexAI Version:** 2.0.0  
**Last Updated:** 2024  
**License:** MIT

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` file for full details.

---

⭐ **Found this project helpful? Please star the repository!**

**LexAI — Intelligent Legal Reasoning Through Multi-Agent Collaboration**
