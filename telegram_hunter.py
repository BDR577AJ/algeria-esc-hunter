import json
import os
import time
import requests

from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from discovery import discover
from crawler import fetch_extract_worker


load_dotenv()


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SENT_FILE = "sent_opportunities.json"

CHECK_INTERVAL = int(
    os.getenv("CHECK_INTERVAL", "1800")
)

# ---------------------------------
# SPEED SETTINGS
# ---------------------------------

# Maximum simultaneous website workers.
# 8 is deliberately conservative because
# the Youth Portal previously returned 429.
MAX_WORKERS = int(
    os.getenv("MAX_WORKERS", "8")
)

# None = ALL opportunities.
# Example: 10 = test first 10 only.
TEST_LIMIT = None


def load_sent():

    if not os.path.exists(SENT_FILE):
        return set()

    try:

        with open(
            SENT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return set(
                json.load(f)
            )

    except Exception:

        return set()


def save_sent(sent):

    with open(
        SENT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            sorted(sent),
            f,
            ensure_ascii=False,
            indent=2
        )


def send_telegram(item):

    url = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )

    title = item.get(
        "title",
        "ESC Opportunity"
    )

    location = item.get(
        "location",
        "Unknown"
    )

    deadline = item.get(
        "deadline",
        "Not specified"
    )

    opportunity_url = item.get(
        "url",
        ""
    )

    text = (
        "🇩🇿 ESC Opportunity\n\n"
        f"📌 {title}\n"
        f"📍 {location}\n"
        f"📅 Deadline: {deadline}\n\n"
        f"🔗 Apply:\n{opportunity_url}"
    )

    try:

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False,
            },
            timeout=30
        )

    except Exception as error:

        print(
            "[Telegram] Connection error:",
            error
        )

        return False

    if response.status_code != 200:

        print(
            "[Telegram] HTTP error:",
            response.status_code
        )

        print(
            response.text
        )

        return False

    try:

        data = response.json()

    except Exception:

        print(
            "[Telegram] Invalid response:",
            response.text
        )

        return False

    if not data.get("ok"):

        print(
            "[Telegram] API error:",
            data
        )

        return False

    print(
        "[Telegram] SENT:",
        title
    )

    return True


def check_one(url):

    """
    Worker function.

    Returns:
        item or None
    """

    try:

        item, _ = fetch_extract_worker(
            url
        )

        return item

    except Exception as error:

        print(
            "[Worker] Error:",
            url,
            "|",
            error
        )

        return None


def scan_once(sent):

    print()
    print("=" * 60)
    print("NEW ESC SCAN")
    print("=" * 60)

    # ---------------------------------
    # DISCOVERY
    # ---------------------------------

    urls = discover()

    if not urls:

        print(
            "[Hunter] No opportunities discovered."
        )

        return sent

    # ---------------------------------
    # OPTIONAL TEST LIMIT
    # ---------------------------------

    if TEST_LIMIT:

        urls = urls[:TEST_LIMIT]

        print(
            "[Hunter] TEST MODE:",
            f"first {TEST_LIMIT}"
        )

    else:

        print(
            "[Hunter] FULL MODE:",
            "all discovered opportunities"
        )

    print(
        "[Hunter] Opportunities:",
        len(urls)
    )

    print(
        "[Hunter] Workers:",
        MAX_WORKERS
    )

    # ---------------------------------
    # COUNTERS
    # ---------------------------------

    checked = 0
    eligible = 0
    sent_count = 0
    errors = 0

    # ---------------------------------
    # PARALLEL CRAWLING
    # ---------------------------------

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                check_one,
                url
            ): url
            for url in urls
        }

        try:

            for future in as_completed(
                futures
            ):

                url = futures[
                    future
                ]

                checked += 1

                try:

                    item = future.result()

                except Exception as error:

                    errors += 1

                    print(
                        "[Hunter] Worker exception:",
                        error
                    )

                    continue

                if not item:

                    errors += 1

                    print(
                        f"[Hunter] "
                        f"{checked}/{len(urls)} "
                        "FAILED"
                    )

                    continue

                title = item.get(
                    "title",
                    "Unknown"
                )

                status = item.get(
                    "algeria_status"
                )

                # ---------------------------------
                # ALGERIA FILTER
                # ---------------------------------

                if status != "ELIGIBLE":

                    print(
                        f"[Hunter] "
                        f"{checked}/{len(urls)} "
                        f"NOT ELIGIBLE | "
                        f"{title}"
                    )

                    continue

                eligible += 1

                opportunity_url = item.get(
                    "url",
                    url
                )

                print(
                    f"[Hunter] "
                    f"{checked}/{len(urls)} "
                    f"🇩🇿 ELIGIBLE | "
                    f"{title}"
                )

                # ---------------------------------
                # DUPLICATE
                # ---------------------------------

                if opportunity_url in sent:

                    print(
                        "[Hunter] Already sent:",
                        title
                    )

                    continue

                # ---------------------------------
                # TELEGRAM
                # ---------------------------------

                if send_telegram(
                    item
                ):

                    sent.add(
                        opportunity_url
                    )

                    save_sent(
                        sent
                    )

                    sent_count += 1

                    # Small Telegram delay.
                    time.sleep(1)

        except KeyboardInterrupt:

            print(
                "\n[Hunter] Stopping workers..."
            )

            executor.shutdown(
                wait=False,
                cancel_futures=True
            )

            raise

    # ---------------------------------
    # SUMMARY
    # ---------------------------------

    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)

    print(
        "[Hunter] Checked:",
        checked
    )

    print(
        "[Hunter] Algeria eligible:",
        eligible
    )

    print(
        "[Hunter] New Telegram messages:",
        sent_count
    )

    print(
        "[Hunter] Errors:",
        errors
    )

    print(
        "[Hunter] Total saved:",
        len(sent)
    )

    return sent


def main():

    # ---------------------------------
    # TELEGRAM CONFIG
    # ---------------------------------

    if not TOKEN:

        print(
            "ERROR: TELEGRAM_BOT_TOKEN "
            "missing from .env"
        )

        return

    if not CHAT_ID:

        print(
            "ERROR: TELEGRAM_CHAT_ID "
            "missing from .env"
        )

        return

    # ---------------------------------
    # LOAD SENT
    # ---------------------------------

    sent = load_sent()

    # ---------------------------------
    # START
    # ---------------------------------

    print(
        "======================================"
    )

    print(
        "🇩🇿 ESC TELEGRAM HUNTER"
    )

    print(
        "======================================"
    )

    print(
        "Previously sent:",
        len(sent)
    )

    print(
        "Workers:",
        MAX_WORKERS
    )

    if TEST_LIMIT:

        print(
            "Mode: TEST"
        )

        print(
            "Limit:",
            TEST_LIMIT
        )

    else:

        print(
            "Mode: FULL"
        )

        print(
            "Limit: ALL"
        )

    print(
        "Check interval:",
        CHECK_INTERVAL,
        "seconds"
    )

    # ---------------------------------
    # CONTINUOUS SCAN
    # ---------------------------------

    while True:

        try:

            sent = scan_once(
                sent
            )

        except KeyboardInterrupt:

            print(
                "\n[Hunter] Stopped."
            )

            break

        except Exception as error:

            print(
                "[Hunter] Scan error:",
                error
            )

        print()

        print(
            f"[Hunter] Next scan in "
            f"{CHECK_INTERVAL} seconds."
        )

        try:

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "\n[Hunter] Stopped."
            )

            break


if __name__ == "__main__":

    main()