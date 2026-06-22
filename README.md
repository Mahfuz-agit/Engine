# KnowledgeMaster

Auto-generates knowledge graphs 24/7 using Groq AI + public internet.
Learn any topic. Take exams. Master everything.

## Setup

### 1. Fork this repo

### 2. Add secret
`Settings → Secrets → Actions → New secret`
- Name: `GROQ_API_KEY`
- Value: your key from [console.groq.com](https://console.groq.com)

### 3. Enable GitHub Pages
`Settings → Pages → Source: GitHub Actions`

### 4. Enable GitHub Actions
`Actions tab → Enable workflows`

### 5. Run manually first
`Actions → Knowledge Graph Generator → Run workflow`

---

## How it works

```
Every 2 hours:
Groq generates topic →
Wikipedia + OpenAlex + RSS + Archive.org fetch content →
Wikimedia fetches images →
Groq builds knowledge graph (15-40 nodes, 20+ edges) →
Groq quality checks (score ≥ 80) →
Groq generates exam (10 questions) →
All merged into master graph →
GitHub Pages deploys
```

## File structure

```
engine/         Python pipeline
data/topics/    Per-topic JSON graphs
data/exams/     Per-topic exam JSON
data/master_graph.json  All topics merged
web/            GitHub Pages frontend
logs/           Run history
```

## Limits (Groq free tier)

| Metric | Limit | Used |
|--------|-------|------|
| RPD | 14,400 | ~36/day |
| RPM | 30 | 3/run max |
| Runs/day | 12 | 12 |

## Stack

- **AI**: Groq (Llama 3.3 70B) — free
- **Content**: Wikipedia, OpenAlex, CommonCrawl, Archive.org, RSS
- **Images**: Wikimedia Commons (CC licensed)
- **Hosting**: GitHub Pages — free
- **Runner**: GitHub Actions — free
