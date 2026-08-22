import csv
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from playwright.sync_api import sync_playwright


WORKERS = int(os.getenv("WORKERS", "50"))

BASE_URL = "https://youth.europa.eu"

DISCOVERY_URL = (
    f"{BASE_URL}/go-abroad/volunteering/"
    "opportunities_en"
)

JSON_FILE = Path("eligible_results.json")
CSV_FILE = Path("eligible_results.csv")


print_lock = threading.Lock()


def safe_print(*args):
    with print_lock:
        print(*args, flush=True)


def get_api_url():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            locale="en-US"
        )

        page = context.new_page()

        api_url = None

        def response_handler(response):

            nonlocal api_url

            url = response.url

            if (
                "/api/rest/eyp/v1/search_en"
                in url
                and "type=Opportunity"
                in url
                and "size=" in url
            ):

                # Prefer the large result request.
                if "size=1169" in url:
                    api_url = url

        page.on(
            "response",
            response_handler
        )

        try:

            safe_print(
                "[API] Opening Youth Portal..."
            )

            page.goto(
                DISCOVERY_URL,
                wait_until="domcontentloaded",
                timeout=120000
            )

            page.wait_for_timeout(
                10000
            )

            return api_url

        finally:

            context.close()
            browser.close()


def get_api_data(api_url):

    with sync_playwright() as p:

        request = p.request.new_context()

        try:

            response = request.get(
                api_url,
                timeout=120000
            )

            safe_print(
                "[API] Status:",
                response.status
            )

            if response.status != 200:
                return None

            return response.json()

        finally:

            request.dispose()


def build_urls(data):

    hits = (
        data
        .get("hits", {})
        .get("hits", [])
    )

    urls = []

    for hit in hits:

        source = hit.get(
            "_source",
            {}
        )

        opid = (
            source.get("opid")
            or source.get("id")
            or hit.get("_id")
        )

        if not opid:
            continue

        urls.append(
            f"{BASE_URL}/solidarity/opportunity/"
            f"{opid}_en"
        )

    return sorted(
        set(urls)
    )


def extract_page(page, url):

    for attempt in range(1, 4):

        try:

            safe_print(
                f"[Worker] {url} "
                f"(attempt {attempt}/3)"
            )

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000
            )

            if response:

                status = response.status

                if status == 429:

                    safe_print(
                        "[429] Waiting..."
                    )

                    time.sleep(
                        5 * attempt
                    )

                    continue

                if status >= 500:

                    time.sleep(
                        3 * attempt
                    )

                    continue

            # Give the page a short time to
            # render dynamic content.
            page.wait_for_timeout(
                1000
            )

            return page.content()

        except Exception as error:

            safe_print(
                f"[Retry] {attempt}/3 | "
                f"{type(error).__name__}"
            )

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

    return None


def extract_algeria_status(html):

    if not html:
        return "UNKNOWN"

    text = html.lower()

    # The crawler's existing logic looks for
    # participant-country information.
    #
    # We deliberately only classify explicit
    # Algeria mentions here.

    if "algeria" not in text:
        return "NOT_LISTED"

    # More conservative check.
    patterns = [
        "algeria",
        "algérie",
        "dz",
    ]

    if any(
        pattern in text
        for pattern in patterns
    ):
        return "POSSIBLE"

    return "NOT_LISTED"


def parse_result(url, html):

    """
    Uses the existing crawler extractor.

    Importing it here avoids duplicating the
    project's detailed extraction rules.
    """

    try:

        from bs4 import BeautifulSoup

        from crawler import extract

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        item, digest = extract(
            url,
            html
        )

        return item

    except Exception as error:

        safe_print(
            f"[Extract error] {url} | {error}"
        )

        return None


def worker(url):

    with sync_playwright() as p:

        browser = None
        context = None
        page = None

        try:

            browser = p.chromium.launch(
                headless=True
            )

            context = browser.new_context(
                locale="en-US"
            )

            page = context.new_page()

            html = extract_page(
                page,
                url
            )

            if not html:
                return None

            item = parse_result(
                url,
                html
            )

            if not item:
                return None

            if (
                item.get(
                    "algeria_status"
                )
                == "ELIGIBLE"
            ):

                item["url"] = url

                return item

            return None

        except Exception as error:

            safe_print(
                f"[Worker error] "
                f"{url} | {error}"
            )

            return None

        finally:

            try:

                if context:
                    context.close()

            except Exception:
                pass

            try:

                if browser:
                    browser.close()

            except Exception:
                pass


def save_results(results):

    results = sorted(
        results,
        key=lambda x: x.get(
            "match_score",
            0
        ),
        reverse=True
    )

    # -----------------------------
    # JSON
    # -----------------------------

    with JSON_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    # -----------------------------
    # CSV
    # -----------------------------

    fields = [
        "title",
        "location",
        "deadline",
        "project_code",
        "algeria_status",
        "housing",
        "food",
        "travel",
        "pocket_money",
        "match_score",
        "url",
    ]

    with CSV_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )

        writer.writeheader()

        for item in results:
            writer.writerow(item)

    safe_print(
        "[SAVE] eligible_results.json"
    )

    safe_print(
        "[SAVE] eligible_results.csv"
    )


def main():

    start_time = time.time()

    safe_print(
        "================================"
    )

    safe_print(
        " FAST VOLUNTEER SCANNER"
    )

    safe_print(
        f" WORKERS: {WORKERS}"
    )

    safe_print(
        "================================"
    )

    # -----------------------------
    # API
    # -----------------------------

    api_url = get_api_url()

    if not api_url:

        safe_print(
            "[ERROR] API URL not found."
        )

        return

    safe_print(
        "[API] Request found."
    )

    data = get_api_data(
        api_url
    )

    if not data:

        safe_print(
            "[ERROR] API data unavailable."
        )

        return

    total = (
        data
        .get("hits", {})
        .get("total", {})
        .get("value", 0)
    )

    urls = build_urls(
        data
    )

    safe_print(
        f"[API] Total: {total}"
    )

    safe_print(
        f"[API] URLs: {len(urls)}"
    )

    # -----------------------------
    # PARALLEL SCAN
    # -----------------------------

    results = []

    completed = 0

    safe_print(
        "[SCAN] Starting parallel scan..."
    )

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(
                worker,
                url
            ): url
            for url in urls
        }

        for future in as_completed(
            futures
        ):

            completed += 1

            url = futures[
                future
            ]

            try:

                item = future.result()

                if item:

                    results.append(
                        item
                    )

                    safe_print(
                        "🇩🇿 ELIGIBLE | "
                        f"{item.get('title')} | "
                        f"{item.get('location')}"
                    )

            except Exception as error:

                safe_print(
                    f"[Future error] "
                    f"{url} | {error}"
                )

            if (
                completed % 25 == 0
                or completed == len(urls)
            ):

                elapsed = (
                    time.time()
                    - start_time
                )

                rate = (
                    completed / elapsed
                    if elapsed > 0
                    else 0
                )

                safe_print(
                    f"[PROGRESS] "
                    f"{completed}/{len(urls)} "
                    f"({rate:.2f}/sec)"
                )

    # -----------------------------
    # SCORE
    # -----------------------------

    try:

        from filter import (
            filter_results
        )

        results = filter_results(
            results
        )

    except Exception as error:

        safe_print(
            f"[Score error] {error}"
        )

    save_results(
        results
    )

    elapsed = (
        time.time()
        - start_time
    )

    safe_print(
        "================================"
    )

    safe_print(
        "FINAL RESULTS"
    )

    safe_print(
        "================================"
    )

    safe_print(
        f"API opportunities: {total}"
    )

    safe_print(
        f"URLs scanned: {len(urls)}"
    )

    safe_print(
        f"🇩🇿 Algeria eligible: {len(results)}"
    )

    safe_print(
        f"Time: {elapsed:.1f} seconds"
    )

    for item in results:

        safe_print(
            f"{item.get('match_score', 0)}/100 | "
            f"{item.get('title')} | "
            f"{item.get('location')} | "
            f"{item.get('deadline')}"
        )


if __name__ == "__main__":
    main()