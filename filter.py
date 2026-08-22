import json
from pathlib import Path


RESULTS_FILE = Path("results.json")


def calculate_score(item):
    score = 0

    if item.get("algeria_status") == "ELIGIBLE":
        score += 40

    if item.get("housing") == "YES":
        score += 15

    if item.get("food") == "YES":
        score += 10

    if item.get("travel") == "YES":
        score += 10

    if item.get("pocket_money") == "YES":
        score += 10

    if item.get("age"):
        score += 5

    if item.get("status") == "OPEN":
        score += 10

    return max(0, min(100, score))


def filter_results(items):

    results = []

    for item in items:

        if item.get("algeria_status") != "ELIGIBLE":
            continue

        item = dict(item)

        item["match_score"] = calculate_score(item)

        results.append(item)

    results.sort(
        key=lambda x: x.get(
            "match_score",
            0
        ),
        reverse=True
    )

    return results


def save_results(items):

    RESULTS_FILE.write_text(
        json.dumps(
            items,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"[Filter] Saved {len(items)} "
        f"results to {RESULTS_FILE}"
    )


def load_results():

    if not RESULTS_FILE.exists():
        return []

    try:

        return json.loads(
            RESULTS_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return []