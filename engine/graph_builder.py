import json
import os
import time
from groq import Groq
from pathlib import Path

ROOT = Path(__file__).parent.parent
CFG = json.loads((ROOT / "config/settings.json").read_text())
client = Groq(api_key=os.environ["GROQ_API_KEY"])


def build_graph(topic_data: dict, content: dict, images: list) -> dict:
    topic = topic_data["topic"]
    subtopics = topic_data.get("subtopics", [])

    wiki_summary = content.get("wikipedia", {}).get("summary", "")[:2000]
    wiki_sections = content.get("wikipedia", {}).get("sections", [])
    papers = content.get("academic_papers", [])
    news = content.get("news_articles", [])

    papers_text = "\n".join([
        f"- {p['title']}: {p['abstract'][:300]}" for p in papers[:3]
    ])
    news_text = "\n".join([
        f"- {n['title']}: {n['summary'][:200]}" for n in news[:3]
    ])
    sections_text = "\n".join([
        f"[{s['title']}]: {s['text'][:400]}" for s in wiki_sections[:4]
    ])

    prompt = f"""You are a world-class knowledge graph architect.

Topic: {topic}
Subtopics: {json.dumps(subtopics)}

Wikipedia Summary:
{wiki_summary}

Wikipedia Sections:
{sections_text}

Academic Papers:
{papers_text}

Recent News:
{news_text}

Build a MASTERPIECE knowledge graph. Rules:
- Minimum {CFG['content']['min_nodes_per_graph']} nodes, max {CFG['content']['max_nodes_per_graph']}
- Minimum {CFG['content']['min_edges_per_graph']} edges
- Max depth: {CFG['content']['max_depth']} levels
- Every node must have: id, label, type, depth, description, importance (1-10)
- Every edge must have: source, target, relation, strength (1-10), description
- Node types: core, concept, application, example, person, event, formula, fact
- Relations: "is_part_of", "leads_to", "is_type_of", "discovered_by", "used_in", "related_to", "depends_on", "contrasts_with", "evolved_from", "enables"
- importance >= 8 for core nodes
- Include historical context, key scientists, real applications

Return ONLY this JSON structure, nothing else:
{{
  "topic": "{topic}",
  "category": "{topic_data.get('category', '')}",
  "description": "2-3 sentence overview",
  "nodes": [
    {{
      "id": "node_id",
      "label": "Node Label",
      "type": "core|concept|application|example|person|event|formula|fact",
      "depth": 0,
      "description": "detailed description",
      "importance": 9,
      "fun_fact": "interesting fact about this"
    }}
  ],
  "edges": [
    {{
      "source": "node_id_1",
      "target": "node_id_2",
      "relation": "relation_type",
      "strength": 8,
      "description": "why these are connected"
    }}
  ],
  "key_takeaways": ["takeaway1", "takeaway2", "takeaway3"],
  "real_world_impact": "paragraph about real world impact"
}}"""

    for attempt in range(CFG["groq"]["retry_attempts"]):
        try:
            res = client.chat.completions.create(
                model=CFG["groq"]["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=CFG["groq"]["max_tokens"],
                temperature=0.5
            )
            raw = res.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            graph = json.loads(raw)
            graph["images"] = images
            graph["sources"] = {
                "wikipedia_url": content.get("wikipedia", {}).get("url", ""),
                "papers": [{"title": p["title"], "url": p["url"]} for p in papers[:3]],
                "news": [{"title": n["title"], "url": n["url"]} for n in news[:3]]
            }
            print(f"[graph_builder] Built graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
            return graph
        except Exception as e:
            print(f"[graph_builder] attempt {attempt+1} failed: {e}")
            time.sleep(CFG["groq"]["retry_delay_seconds"])

    raise RuntimeError(f"Failed to build graph for topic: {topic}")


if __name__ == "__main__":
    sample_topic = {
        "topic": "Quantum Entanglement",
        "category": "physics",
        "subtopics": ["superposition", "Bell theorem", "photon", "EPR paradox", "quantum computing"]
    }
    sample_content = {"wikipedia": {"summary": "Quantum entanglement is...", "sections": [], "url": ""}, "academic_papers": [], "news_articles": []}
    graph = build_graph(sample_topic, sample_content, [])
    print(json.dumps(graph, indent=2))
