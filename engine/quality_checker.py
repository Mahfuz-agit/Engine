import json
import os
import time
from groq import Groq
from pathlib import Path

ROOT = Path(__file__).parent.parent
CFG = json.loads((ROOT / "config/settings.json").read_text())
client = Groq(api_key=os.environ["GROQ_API_KEY"])


def structural_check(graph: dict) -> dict:
    issues = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = {n["id"] for n in nodes}

    if len(nodes) < CFG["content"]["min_nodes_per_graph"]:
        issues.append(f"Too few nodes: {len(nodes)}")
    if len(edges) < CFG["content"]["min_edges_per_graph"]:
        issues.append(f"Too few edges: {len(edges)}")

    for edge in edges:
        if edge["source"] not in node_ids:
            issues.append(f"Edge source missing: {edge['source']}")
        if edge["target"] not in node_ids:
            issues.append(f"Edge target missing: {edge['target']}")

    for node in nodes:
        if not node.get("description"):
            issues.append(f"Node missing description: {node['id']}")
        if node.get("importance", 0) < 1:
            issues.append(f"Node importance invalid: {node['id']}")

    has_core = any(n["type"] == "core" for n in nodes)
    if not has_core:
        issues.append("No core node found")

    score = max(0, 100 - len(issues) * 10)
    return {"score": score, "issues": issues, "node_count": len(nodes), "edge_count": len(edges)}


def ai_quality_check(graph: dict) -> dict:
    topic = graph.get("topic", "")
    nodes_preview = [{"id": n["id"], "label": n["label"], "type": n["type"]} for n in graph.get("nodes", [])[:20]]
    edges_preview = graph.get("edges", [])[:15]

    prompt = f"""You are a knowledge graph quality auditor.

Topic: {topic}
Nodes ({len(graph.get('nodes', []))} total): {json.dumps(nodes_preview)}
Edges ({len(graph.get('edges', []))} total): {json.dumps(edges_preview)}
Key Takeaways: {json.dumps(graph.get('key_takeaways', []))}

Rate this knowledge graph on:
1. Completeness (covers the topic fully)
2. Accuracy (concepts are correct)
3. Connectivity (well-connected graph)
4. Educational value (useful for learning)
5. Depth (goes deep enough)

Return ONLY JSON:
{{
  "completeness": 85,
  "accuracy": 90,
  "connectivity": 80,
  "educational_value": 88,
  "depth": 82,
  "overall_score": 85,
  "missing_concepts": ["concept1", "concept2"],
  "strengths": ["strength1", "strength2"],
  "verdict": "PASS or FAIL"
}}"""

    for attempt in range(CFG["groq"]["retry_attempts"]):
        try:
            res = client.chat.completions.create(
                model=CFG["groq"]["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3
            )
            raw = res.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as e:
            print(f"[quality_checker] attempt {attempt+1} failed: {e}")
            time.sleep(CFG["groq"]["retry_delay_seconds"])

    return {"overall_score": 0, "verdict": "FAIL", "missing_concepts": [], "strengths": []}


def run(graph: dict) -> dict:
    structural = structural_check(graph)
    ai_check = ai_quality_check(graph)

    combined_score = (structural["score"] + ai_check.get("overall_score", 0)) / 2
    passed = combined_score >= CFG["quality"]["min_quality_score"]

    result = {
        "structural": structural,
        "ai_review": ai_check,
        "combined_score": round(combined_score, 1),
        "passed": passed,
        "verdict": "PASS" if passed else "FAIL"
    }

    print(f"[quality_checker] Score: {combined_score:.1f} → {result['verdict']}")
    return result


if __name__ == "__main__":
    sample_graph = {
        "topic": "Test",
        "nodes": [{"id": "n1", "label": "Test", "type": "core", "description": "test", "importance": 9}],
        "edges": [],
        "key_takeaways": []
    }
    print(json.dumps(run(sample_graph), indent=2))
