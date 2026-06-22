import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "logs/run_history.json"

import engine.topic_generator as topic_gen
import engine.content_fetcher as content_fetch
import engine.image_fetcher as image_fetch
import engine.graph_builder as graph_build
import engine.quality_checker as quality_check
import engine.exam_generator as exam_gen
import engine.master_merger as merger

CFG = json.loads((ROOT / "config/settings.json").read_text())


def log(entry: dict):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if LOG_FILE.exists():
        history = json.loads(LOG_FILE.read_text())
    history.append(entry)
    history = history[-500:]
    LOG_FILE.write_text(json.dumps(history, indent=2))


def run():
    start = datetime.utcnow()
    log_entry = {"started_at": start.isoformat(), "status": "running"}

    try:
        print("=" * 50)
        print(f"[pipeline] START: {start.isoformat()}")
        print("=" * 50)

        # Step 1: Generate topic
        print("\n[STEP 1] Generating topic...")
        topic_data = topic_gen.run()
        log_entry["topic"] = topic_data["topic"]
        time.sleep(3)

        # Step 2: Fetch content
        print("\n[STEP 2] Fetching content...")
        content = content_fetch.fetch_all(topic_data["topic"])
        log_entry["sources_found"] = content["total_sources"]
        time.sleep(2)

        # Step 3: Fetch images
        print("\n[STEP 3] Fetching images...")
        images = image_fetch.run(topic_data["topic"], topic_data.get("subtopics", []))
        log_entry["images_found"] = len(images)
        time.sleep(2)

        # Step 4: Build graph (with quality retry)
        print("\n[STEP 4] Building knowledge graph...")
        max_attempts = CFG["quality"]["max_regenerate_attempts"]
        graph = None
        quality_result = None

        for attempt in range(max_attempts):
            graph = graph_build.build_graph(topic_data, content, images)
            time.sleep(3)

            print(f"\n[STEP 4b] Quality check (attempt {attempt+1})...")
            quality_result = quality_check.run(graph)
            graph["quality"] = quality_result

            if quality_result["passed"]:
                break
            elif attempt < max_attempts - 1:
                print(f"[pipeline] Quality FAIL ({quality_result['combined_score']}), retrying...")
                time.sleep(5)

        log_entry["quality_score"] = quality_result["combined_score"]
        log_entry["quality_passed"] = quality_result["passed"]
        time.sleep(3)

        # Step 5: Generate exam
        print("\n[STEP 5] Generating exam...")
        exam = exam_gen.run(graph)
        graph["exam_generated"] = True
        log_entry["exam_questions"] = len(exam.get("questions", []))
        time.sleep(3)

        # Step 6: Merge into master
        print("\n[STEP 6] Merging into master graph...")
        master = merger.run(graph)
        log_entry["master_total_topics"] = master["total_topics"]

        end = datetime.utcnow()
        duration = (end - start).total_seconds()
        log_entry.update({
            "status": "success",
            "ended_at": end.isoformat(),
            "duration_seconds": round(duration, 1)
        })

        print("\n" + "=" * 50)
        print(f"[pipeline] SUCCESS in {duration:.1f}s")
        print(f"[pipeline] Topic: {topic_data['topic']}")
        print(f"[pipeline] Nodes: {len(graph.get('nodes', []))}")
        print(f"[pipeline] Edges: {len(graph.get('edges', []))}")
        print(f"[pipeline] Quality: {quality_result['combined_score']}")
        print(f"[pipeline] Master topics: {master['total_topics']}")
        print("=" * 50)

    except Exception as e:
        log_entry["status"] = "error"
        log_entry["error"] = str(e)
        log_entry["traceback"] = traceback.format_exc()
        print(f"[pipeline] ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        log(log_entry)


if __name__ == "__main__":
    run()
