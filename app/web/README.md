# Learn Agentic AI — Educational Platform + Wiki Knowledge Base

## Overview

**Learn Agentic AI** is a comprehensive educational platform for learning about Agentic Artificial Intelligence. It includes an **interactive learning website** and a full-featured **Wiki Knowledge Base** inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/1dd0294ef9567971c1e4348a90d69285) concept.

## 🎯 Project Goals

- **Demystify Agentic AI**: Make complex AI concepts accessible to beginners
- **Interactive Learning**: Hands-on examples, quizzes, and demos
- **Living Knowledge Base**: A wiki-style system with interconnected articles, backlinks, categories, and full-text search
- **Responsive Design**: Works on desktop, tablet, and mobile

---

## ✨ Features Currently Implemented

### 1. Main Educational Site (`index.html`)
- Hero section with animated neural network visualization
- "Understanding Agentic AI" cards explaining key concepts
- Learning path progression (Foundation → Types → Applications → Build)
- Historical timeline of AI evolution (1950s–2020s)
- Interactive examples: Chatbot Agent, Decision Maker, Task Planner
- 5-question knowledge quiz with scoring & explanations
- Curated learning resources (books, courses, platforms, communities)
- Responsive navbar with mobile hamburger menu

### 2. Wiki Knowledge Base (`wiki.html`) ⭐ NEW
Inspired by Karpathy's LLM Wiki — a comprehensive, interconnected knowledge base:

#### Core Features
- **15 in-depth articles** across 8 categories covering all aspects of Agentic AI
- **Full-text search** with real-time results (Ctrl+K shortcut)
- **Wiki-style `[[backlinks]]`** connecting articles together
- **Category browsing** with color-coded categories and article counts
- **Difficulty filtering** (Beginner, Intermediate, Advanced)
- **Tag cloud** with clickable tags for filtering
- **Markdown rendering** via Marked.js with tables, code blocks, and lists
- **Table of Contents** auto-generated from article headings
- **Knowledge Graph** — interactive canvas visualization of article relationships
- **Dark mode / Light mode** toggle with localStorage persistence
- **Breadcrumb navigation** for easy wayfinding
- **Article metadata** (word count, category, difficulty, last edited)
- **Hash-based routing** for deep-linking to articles/categories/tags
- **Responsive sidebar** collapsible on desktop, overlay on mobile

#### Wiki Categories
| Category | Color | Description |
|----------|-------|-------------|
| Foundations | 🟣 Indigo | Core concepts and fundamentals |
| Architecture | 🟡 Amber | Design patterns, components, system architecture |
| Agents | 🟢 Emerald | Types, behaviors, capabilities |
| Training | 🔴 Red | Learning methods, RLHF, optimization |
| Applications | 🟣 Purple | Real-world applications |
| Tools | 🔵 Cyan | Frameworks, libraries, developer tools |
| Safety | 🩷 Pink | Alignment, safety, responsible AI |
| Research | 🟢 Teal | Cutting-edge research, future directions |

#### Wiki Articles
1. **Agentic AI Overview** — Comprehensive introduction to autonomous AI systems
2. **AI Agent Architecture** — Core loop, memory systems, design patterns
3. **Large Language Models** — Transformers, training pipeline, key models
4. **Types of AI Agents** — Taxonomy from reflex to learning agents
5. **Tool Use in AI Agents** — Function calling, ReAct, MCP protocol
6. **Multi-Agent Systems** — Communication, coordination, frameworks
7. **Prompt Engineering** — Zero-shot, few-shot, CoT, system prompts
8. **RAG and Knowledge Retrieval** — Vector databases, chunking, advanced RAG
9. **Reinforcement Learning** — Q-learning, policy gradient, RLHF
10. **AI Safety and Alignment** — Constitutional AI, interpretability, governance
11. **Agent Frameworks and Tools** — LangChain, AutoGen, CrewAI comparison
12. **Autonomous Coding Agents** — Copilot, Cursor, Devin, SWE-bench
13. **Agentic AI in Science** — AlphaFold, GNoME, AI Scientist
14. **Agentic AI in Business** — Customer service, operations, enterprise platforms
15. **The Future of Agentic AI** — Personal AI, AGI, societal transformation

---

## 📁 File Structure

```
project/
├── index.html              # Main educational site
├── wiki.html               # Wiki knowledge base ⭐
├── css/
│   ├── style.css           # Main site styles
│   ├── responsive.css      # Main site responsive styles
│   └── wiki.css            # Wiki styles (light/dark theme) ⭐
├── js/
│   ├── main.js             # Main site JavaScript
│   └── wiki.js             # Wiki engine JavaScript ⭐
└── README.md               # This file
```

---

## 🔗 Functional Entry URIs

| Path | Description |
|------|-------------|
| `index.html` | Main educational site |
| `wiki.html` | Wiki home page with category overview & stats |
| `wiki.html#article/{slug}` | Direct link to a specific wiki article |
| `wiki.html#category/{name}` | Filter articles by category |
| `wiki.html#tag/{name}` | Filter articles by tag |
| `wiki.html#difficulty/{level}` | Filter by difficulty (Beginner/Intermediate/Advanced) |
| `wiki.html#all` | View all articles list |
| `wiki.html#graph` | Interactive knowledge graph visualization |
| `wiki.html#recent` | Recently updated articles |

### Example Deep Links
- `wiki.html#article/agentic-ai-overview` — Agentic AI Overview article
- `wiki.html#article/large-language-models` — LLM article
- `wiki.html#category/Architecture` — Architecture category
- `wiki.html#tag/safety` — Articles tagged with "safety"
- `wiki.html#difficulty/Beginner` — Beginner-level articles

---

## 🗄️ Data Model

### Table: `wiki_articles`

| Field | Type | Description |
|-------|------|-------------|
| `id` | text | Unique identifier (UUID, auto-generated) |
| `title` | text | Article title |
| `slug` | text | URL-friendly identifier |
| `summary` | text | Brief excerpt |
| `content` | rich_text | Full article in Markdown with `[[wiki links]]` |
| `category` | text | Primary category (enum: 8 categories) |
| `tags` | array | Array of tag strings |
| `backlinks` | array | Array of article slugs this article links to |
| `difficulty` | text | Beginner / Intermediate / Advanced |
| `word_count` | number | Approximate word count |
| `last_edited` | text | Date string of last edit |
| `status` | text | Published / Draft / Review |

Data is served via the RESTful Table API at `tables/wiki_articles`.

---

## 🧪 Technical Implementation

### Wiki Architecture (Karpathy-inspired)
- **Knowledge Compilation**: Articles are interconnected via `[[wiki links]]` that are parsed and resolved at render time
- **Backlinks**: Bidirectional — each article shows both "Links To" and "Linked From" sections
- **Knowledge Graph**: Force-directed graph visualization using Canvas API
- **Search**: Client-side full-text search across title, summary, content, and tags
- **Markdown**: Rendered via Marked.js with support for tables, code blocks, and inline formatting

### Frontend Libraries (CDN)
- **Marked.js**: Markdown → HTML rendering
- **Font Awesome 6**: Icons throughout the interface
- **Google Fonts**: Inter + JetBrains Mono for typography

### Key JavaScript Features
- Hash-based SPA routing
- Real-time search with debouncing
- Force-directed graph layout algorithm
- Dark/light theme with system preference detection
- Responsive sidebar with mobile overlay
- Keyboard shortcuts (Ctrl+K for search)

---

## 🚀 Recommended Next Steps

1. **Add article editor**: Enable creating/editing articles directly in the wiki UI
2. **Full-text indexing**: Implement more sophisticated search with ranking
3. **Article versioning**: Track edit history and diffs
4. **Export**: Allow exporting articles as Markdown or PDF
5. **Agentic ingestion**: Pipeline to automatically compile new articles from raw sources (à la Karpathy's LLM Wiki)
6. **Improved graph**: Zoom, pan, and filtering in the knowledge graph
7. **User bookmarks**: Allow saving favorite articles
8. **Wiki linting**: Detect broken links, missing backlinks, and orphaned articles

---

## 📄 License

Created for educational purposes. Feel free to use, modify, and distribute.
