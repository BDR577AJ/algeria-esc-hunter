import csv
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://youth.europa.eu"

WORKERS = int(os.getenv("WORKERS", "20"))

TIMEOUT = (10, 45)

MAX_RETRIES = 3

print_lock = threading.Lock()


def log(*args):
    with print_lock:
        print(*args, flush=True)


def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,"
                  "application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })

    return session


thread_local = threading.local()


def get_session():

    if not hasattr(
        thread_local,
        "session"
    ):

        thread_local.session = (
            create_session()
        )

    return thread_local.session


def fetch_page(url):

    session = get_session()

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                timeout=TIMEOUT
            )

            if response.status_code == 200:

                return response.text

            if response.status_code == 429:

                wait = (
                    5 * attempt
                    + random.uniform(1, 3)
                )

                log(
                    f"[429] Waiting {wait:.1f}s"
                )

                time.sleep(wait)

                continue

            if response.status_code >= 500:

                time.sleep(
                    2 * attempt
                )

                continue

            log(
                f"[HTTP {response.status_code}] "
                f"{url}"
            )

            return None

        except requests.RequestException as error:

            log(
                f"[Retry {attempt}/{MAX_RETRIES}] "
                f"{type(error).__name__}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    2 * attempt
                )

    return None


def extract_basic(
    url,
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    lower = text.lower()

    # IMPORTANT:
    # This is only a preliminary check.
    # Your existing crawler remains the
    # authoritative Algeria eligibility
    # detector.

    if "algeria" not in lower:

        return None

    title = ""

    if soup.title:

        title = soup.title.get_text(
            " ",
            strip=True
        )

    return {
        "url": url,
        "title": title,
        "possible_algeria": True,
    }


def worker(number, url):

    html = fetch_page(
        url
    )

    if not html:

        return None

    result = extract_basic(
        url,
        html
    )

    if result:

        log(
            f"🇩🇿 POSSIBLE | "
            f"{number} | "
            f"{result['title']}"
        )

    return result


def get_api_urls():

    from discovery import discover

    return discover()


def main():

    start = time.time()

    log(
        "================================"
    )

    log(
        " FAST HTTP SCAN"
    )

    log(
        f" WORKERS: {WORKERS}"
    )

    log(
        "================================"
    )

    urls = get_api_urls()

    log(
        f"[Discovery] URLs: {len(urls)}"
    )

    possible = []

    completed = 0

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(
                worker,
                number,
                url
            ): url

            for number, url
            in enumerate(
                urls,
                start=1
            )
        }

        for future in as_completed(
            futures
        ):

            completed += 1

            try:

                result = (
                    future.result()
                )

                if result:

                    possible.append(
                        result
                    )

            except Exception as error:

                url = futures[
                    future
                ]

                log(
                    f"[Error] {url} | "
                    f"{error}"
                )

            if (
                completed % 50 == 0
                or completed == len(urls)
            ):

                elapsed = (
                    time.time()
                    - start
                )

                rate = (
                    completed / elapsed
                    if elapsed
                    else 0
                )

                log(
                    f"[PROGRESS] "
                    f"{completed}/{len(urls)} "
                    f"| {rate:.2f}/sec"
                )

    with open(
        "possible_algeria.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            possible,
            f,
            ensure_ascii=False,
            indent=2
        )

    elapsed = (
        time.time()
        - start
    )

    log(
        "================================"
    )

    log(
        f"Scanned: {len(urls)}"
    )

    log(
        f"Possible Algeria: "
        f"{len(possible)}"
    )

    log(
        f"Time: {elapsed:.1f}s"
    )

    log(
        "Saved: possible_algeria.json"
    )


if __name__ == "__main__":
    main()