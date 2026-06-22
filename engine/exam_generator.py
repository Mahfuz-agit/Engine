import json
import os
import time
from groq import Groq
from pathlib import Path

ROOT = Path(__file__).parent.parent
CFG = json.loads((ROOT / "config/settings.json").read_text())
client = Groq(api_key=os.environ["GROQ_API_KEY"])
EXAM_DIR = ROOT / "data/exams"


def generate_exam(graph: dict) -> dict:
    topic = graph["topic"]
    nodes = graph.get("nodes", [])
    takeaways = graph.get("key_takeaways", [])
    description = graph.get("description", "")

    core_nodes = [n for n in nodes if n.get("importance", 0) >= 7]
    nodes_text = json.dumps([
        {"label": n["label"], "description": n["description"], "fun_fact": n.get("fun_fact", "")}
        for n in core_nodes[:15]
    ])

    mcq_count = CFG["exam"]["mcq_count"]
    short_count = CFG["exam"]["short_answer_count"]

    prompt = f"""You are a world-class exam creator for educational knowledge graphs.

Topic: {topic}
Description: {description}
Key Takeaways: {json.dumps(takeaways)}
Core Concepts: {nodes_text}

Create a {mcq_count + short_count}-question exam. Rules:
- {mcq_count} MCQ questions (4 options each, 1 correct)
- {short_count} short answer questions
- Questions test deep understanding, not memorization
- MCQ wrong options must be plausible (not obvious)
- Each question maps to a node_id from the graph
- Difficulty: mix easy(30%), medium(40%), hard(30%)

Return ONLY JSON:
{{
  "topic": "{topic}",
  "total_questions": {mcq_count + short_count},
  "pass_score": {CFG["exam"]["pass_score"]},
  "questions": [
    {{
      "id": "q1",
      "type": "mcq",
      "difficulty": "easy|medium|hard",
      "question": "question text",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "why this is correct",
      "node_id": "related_node_id",
      "points": 10
    }},
    {{
      "id": "q8",
      "type": "short_answer",
      "difficulty": "medium",
      "question": "question text",
      "sample_answer": "expected answer",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "node_id": "related_node_id",
      "points": 10
    }}
  ]
}}"""

    for attempt in range(CFG["groq"]["retry_attempts"]):
        try:
            res = client.chat.completions.create(
                model=CFG["groq"]["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=CFG["groq"]["max_tokens"],
                temperature=0.6
            )
            raw = res.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            exam = json.loads(raw)
            print(f"[exam_generator] Generated {len(exam['questions'])} questions for: {topic}")
            return exam
        except Exception as e:
            print(f"[exam_generator] attempt {attempt+1} failed: {e}")
            time.sleep(CFG["groq"]["retry_delay_seconds"])

    raise RuntimeError(f"Failed to generate exam for: {topic}")


def save_exam(exam: dict) -> Path:
    EXAM_DIR.mkdir(parents=True, exist_ok=True)
    slug = exam["topic"].lower().replace(" ", "_").replace("/", "_")
    path = EXAM_DIR / f"{slug}_exam.json"
    path.write_text(json.dumps(exam, indent=2))
    print(f"[exam_generator] Saved: {path}")
    return path


def run(graph: dict) -> dict:
    exam = generate_exam(graph)
    save_exam(exam)
    return exam


if __name__ == "__main__":
    sample_graph = {
        "topic": "Quantum Entanglement",
        "description": "Quantum entanglement is a phenomenon...",
        "key_takeaways": ["Particles share state", "Instant correlation", "Used in quantum computing"],
        "nodes": [
            {"id": "n1", "label": "Entanglement", "type": "core", "description": "Core concept", "importance": 10, "fun_fact": "Einstein called it spooky action at a distance"},
        ]
    }
    exam = run(sample_graph)
    print(json.dumps(exam, indent=2))
