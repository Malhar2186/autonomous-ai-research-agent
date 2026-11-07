# 🔬 Autonomous AI Research Agent

An autonomous, multi-tool deep research agent in Python. Given a research objective or query, the agent:
1. **Plans & Decomposes** the topic into targeted investigation areas and query vectors.
2. **Executes Multi-Source Search** across live Web (DuckDuckGo), Knowledge bases (Wikipedia), and Academic papers (arXiv).
3. **Scrapes & Extracts Evidence** using advanced text cleaning (`trafilatura` and `beautifulsoup4`), filtering noise and extracting key metrics, facts, and citations.
4. **Performs Autonomous Gap Reflection**: If crucial information is missing, it dynamically spawns follow-up queries to drill deeper.
5. **Synthesizes Publication-Grade Reports**: Generates structured Markdown reports with executive summaries, technical comparisons, limitations, and full source references with URLs.

---

## 🛠️ Tools & Architecture

| Component | Technology / Library | Purpose |
| :--- | :--- | :--- |
| **Search Engine** | `duckduckgo-search` | Live, privacy-preserving web search without requiring search API keys |
| **Knowledge Base** | `wikipedia` | Canonical definitions and background context |
| **Academic Search** | `arxiv` | Search preprints and peer-reviewed scientific papers |
| **Content Extractor** | `trafilatura` & `beautifulsoup4` | Extracts article body text, strips ads/scripts/nav, handles HTML fallbacks |
| **LLM Engine** | `google-genai`, `openai` | Supports Gemini, OpenAI (GPT-4o), Groq (Llama 3.3), and local Ollama |
| **User Interface** | `rich` | Terminal dashboard, progress tables, styled logs, and status spinners |

---

## 🚀 Quickstart

### 1. Configure API Keys
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` and add your preferred provider credentials. For Google Gemini:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
*(You can also use `LLM_PROVIDER=openai`, `LLM_PROVIDER=groq`, or `LLM_PROVIDER=ollama` for local inference).*

---

### 2. Run the Research Agent

#### Interactive Mode:
Simply run without arguments to get prompted:
```bash
.\.venv\Scripts\python main.py
```

#### Command Line Mode:
```bash
# Standard research
.\.venv\Scripts\python main.py "Agentic AI workflows in software engineering"

# Quick research
.\.venv\Scripts\python main.py "Nuclear Fusion energy progress" --depth quick

# Deep academic research with arXiv papers
.\.venv\Scripts\python main.py "State space models vs Transformers" --depth deep --academic

# Specify custom provider and model
.\.venv\Scripts\python main.py "mRNA vaccine developments" --provider gemini --model gemini-2.5-flash
```

---

## 📂 Output Reports
All reports are automatically written to `./output/` in markdown format:
`./output/research_<topic_slug>_<timestamp>.md`

Each report includes:
- **Executive Summary**
- **Core Background & Fundamentals**
- **Key Findings & Detailed Analysis**
- **Comparative Insights & Technical Nuances** (Markdown Tables)
- **Challenges, Limitations & Open Questions**
- **Future Trajectory & Strategic Takeaways**
- **Complete References & Consulted Sources** (with clickable URLs)

