import json
import os
import time
from groq import Groq
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config/settings.json").read_text())
SOURCES = json.loads((ROOT / "config/sources.json").read_text())
QUEUE_FILE = ROOT / "data/progress/topic_queue.json"

client = Groq(api_key=os.environ["GROQ_API_KEY"])


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text())
    return {"done": [], "failed": [], "current": None}


def save_queue(queue: dict):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def get_done_topics(queue: dict) -> list:
    return queue.get("done", [])


def generate_next_topic(queue: dict) -> str:
    done = get_done_topics(queue)
    categories = SOURCES["topic_categories"]

    prompt = f"""You are a knowledge graph topic generator.

Already covered topics: {json.dumps(done[-50:]) if done else "none"}
Available categories: {json.dumps(categories)}

Generate ONE specific, rich, educational topic that:
- Has not been covered yet
- Has deep interconnected concepts
- Has abundant public domain content
- Is universally important knowledge
- Spans multiple sub-concepts

Return ONLY a JSON object:
{{
  "topic": "exact topic name",
  "category": "category from list",
  "subtopics": ["sub1", "sub2", "sub3", "sub4", "sub5"],
  "reason": "why this topic is important"
}}

No extra text. JSON only."""

    for attempt in range(CONFIG["groq"]["retry_attempts"]):
        try:
            res = client.chat.completions.create(
                model=CONFIG["groq"]["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=CONFIG["groq"]["temperature"]
            )
            raw = res.choices[0].message.content.strip()
            data = json.loads(raw)
            topic = data["topic"]
            if topic not in done:
                return data
        except Exception as e:
            print(f"[topic_generator] attempt {attempt+1} failed: {e}")
            time.sleep(CONFIG["groq"]["retry_delay_seconds"])

    raise RuntimeError("Failed to generate unique topic after retries")


def run() -> dict:
    queue = load_queue()
    topic_data = generate_next_topic(queue)
    queue["current"] = topic_data["topic"]
    save_queue(queue)
    print(f"[topic_generator] Selected: {topic_data['topic']}")
    return topic_data


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
