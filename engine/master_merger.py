import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
TOPICS_DIR = ROOT / "data/topics"
MASTER_FILE = ROOT / "data/master_graph.json"
QUEUE_FILE = ROOT / "data/progress/topic_queue.json"


def load_master() -> dict:
    if MASTER_FILE.exists():
        return json.loads(MASTER_FILE.read_text())
    return {
        "created_at": datetime.utcnow().isoformat(),
        "total_topics": 0,
        "total_nodes": 0,
        "total_edges": 0,
        "topics": [],
        "global_nodes": [],
        "global_edges": [],
        "category_map": {}
    }


def merge_into_master(graph: dict, master: dict) -> dict:
    topic = graph["topic"]
    category = graph.get("category", "general")

    existing_topics = [t["topic"] for t in master["topics"]]
    if topic in existing_topics:
        print(f"[master_merger] Topic already exists: {topic}")
        return master

    slug = topic.lower().replace(" ", "_").replace("/", "_")

    master["topics"].append({
        "topic": topic,
        "slug": slug,
        "category": category,
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
        "description": graph.get("description", ""),
        "added_at": datetime.utcnow().isoformat()
    })

    for node in graph.get("nodes", []):
        global_node = {**node, "topic_slug": slug, "topic": topic}
        global_node["id"] = f"{slug}__{node['id']}"
        master["global_nodes"].append(global_node)

    for edge in graph.get("edges", []):
        global_edge = {
            "source": f"{slug}__{edge['source']}",
            "target": f"{slug}__{edge['target']}",
            "relation": edge.get("relation", "related_to"),
            "strength": edge.get("strength", 5),
            "topic": topic
        }
        master["global_edges"].append(global_edge)

    if category not in master["category_map"]:
        master["category_map"][category] = []
    master["category_map"][category].append(slug)

    master["total_topics"] = len(master["topics"])
    master["total_nodes"] = len(master["global_nodes"])
    master["total_edges"] = len(master["global_edges"])
    master["last_updated"] = datetime.utcnow().isoformat()

    return master


def find_cross_topic_connections(master: dict) -> list:
    cross_edges = []
    topic_core_nodes = {}

    for node in master["global_nodes"]:
        slug = node.get("topic_slug", "")
        if node.get("type") == "core" or node.get("importance", 0) >= 8:
            label_lower = node["label"].lower()
            if label_lower not in topic_core_nodes:
                topic_core_nodes[label_lower] = []
            topic_core_nodes[label_lower].append({"id": node["id"], "slug": slug})

    for label, nodes in topic_core_nodes.items():
        if len(nodes) > 1:
            for i in range(len(nodes) - 1):
                if nodes[i]["slug"] != nodes[i+1]["slug"]:
                    cross_edges.append({
                        "source": nodes[i]["id"],
                        "target": nodes[i+1]["id"],
                        "relation": "cross_topic_connection",
                        "strength": 6,
                        "label": label
                    })

    return cross_edges[:200]


def save_topic_file(graph: dict):
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    slug = graph["topic"].lower().replace(" ", "_").replace("/", "_")
    path = TOPICS_DIR / f"{slug}.json"
    path.write_text(json.dumps(graph, indent=2))
    print(f"[master_merger] Saved topic file: {path}")


def update_queue(topic: str):
    if not QUEUE_FILE.exists():
        return
    queue = json.loads(QUEUE_FILE.read_text())
    if topic not in queue.get("done", []):
        queue.setdefault("done", []).append(topic)
    queue["current"] = None
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def run(graph: dict) -> dict:
    save_topic_file(graph)
    master = load_master()
    master = merge_into_master(graph, master)
    cross = find_cross_topic_connections(master)
    master["cross_topic_edges"] = cross
    MASTER_FILE.write_text(json.dumps(master, indent=2))
    update_queue(graph["topic"])
    print(f"[master_merger] Master: {master['total_topics']} topics, {master['total_nodes']} nodes, {master['total_edges']} edges")
    return master


if __name__ == "__main__":
    sample = {"topic": "Test Topic", "category": "science", "description": "test", "nodes": [], "edges": []}
    print(json.dumps(run(sample), indent=2))
