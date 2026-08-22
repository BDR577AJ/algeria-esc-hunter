import re
import time
import hashlib
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )
}

_PAGE = None
_CONTEXT = None
_BROWSER = None
_PW = None


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def close_browser():
    global _PAGE, _CONTEXT, _BROWSER, _PW

    try:
        if _PAGE:
            _PAGE.close()
    except Exception:
        pass

    try:
        if _CONTEXT:
            _CONTEXT.close()
    except Exception:
        pass

    try:
        if _BROWSER:
            _BROWSER.close()
    except Exception:
        pass

    try:
        if _PW:
            _PW.stop()
    except Exception:
        pass

    _PAGE = None
    _CONTEXT = None
    _BROWSER = None
    _PW = None


def fetch(url, delay=1):
    global _PAGE, _CONTEXT, _BROWSER, _PW

    if delay:
        time.sleep(delay)

    if _PAGE is None:

        from playwright.sync_api import sync_playwright

        _PW = sync_playwright().start()

        _BROWSER = _PW.chromium.launch(
            headless=True
        )

        _CONTEXT = _BROWSER.new_context(
            viewport={
                "width": 1440,
                "height": 900
            },
            user_agent=HEADERS["User-Agent"],
            locale="en-US"
        )

        _PAGE = _CONTEXT.new_page()

        _PAGE.set_default_navigation_timeout(
            120000
        )

    for attempt in range(1, 4):

        try:

            print(
                f"[Crawler] Loading {url} "
                f"(attempt {attempt}/3)"
            )

            _PAGE.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            _PAGE.wait_for_timeout(500)

            return _PAGE.content()

        except Exception as error:

            print(
                f"[Crawler] Error: {error}"
            )

            if attempt < 3:
                time.sleep(1)

    raise RuntimeError(
        f"Failed to load page: {url}"
    )


def label_value(soup, label):

    node = soup.find(
        string=lambda x:
        x and label.lower() in clean(x).lower()
    )

    if not node:
        return ""

    el = node.parent

    for _ in range(5):

        if el:

            text = clean(
                el.get_text(
                    " ",
                    strip=True
                )
            )

            if len(text) > len(label) + 3:
                return text

            el = el.parent

    return ""


def find_field(soup, label):

    # First try exact label.
    node = soup.find(
        string=lambda x:
        x and clean(x).lower() == label.lower()
    )

    if node:

        parent = node.parent

        # Look at the next sibling.
        if parent:

            sibling = parent.find_next_sibling()

            if sibling:

                value = clean(
                    sibling.get_text(
                        " ",
                        strip=True
                    )
                )

                if (
                    value
                    and value.lower() != label.lower()
                ):

                    return value

        # Look at nearby elements.
        current = parent

        for _ in range(5):

            if not current:
                break

            elements = current.find_all(
                recursive=False
            )

            for index, element in enumerate(
                elements
            ):

                element_text = clean(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if (
                    label.lower()
                    not in element_text.lower()
                ):
                    continue

                if index + 1 < len(elements):

                    value = clean(
                        elements[index + 1].get_text(
                            " ",
                            strip=True
                        )
                    )

                    if (
                        value
                        and value.lower()
                        != label.lower()
                    ):

                        return value

            current = current.parent

    # Fallback to the original method.
    value = label_value(
        soup,
        label
    )

    if not value:
        return ""

    value = re.sub(
        rf"^{re.escape(label)}\s*",
        "",
        value,
        flags=re.IGNORECASE
    )

    return clean(value)


def extract(url, html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # -----------------------------
    # TITLE
    # -----------------------------

    h1 = soup.find("h1")

    if h1:

        title = clean(
            h1.get_text(
                " ",
                strip=True
            )
        )

    elif soup.title:

        title = clean(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    else:

        title = ""

    # -----------------------------
    # FULL PAGE TEXT
    # -----------------------------

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # -----------------------------
    # FIELDS
    # -----------------------------

    activity_dates = find_field(
        soup,
        "Activity dates"
    )

    location = find_field(
        soup,
        "Activity location"
    )

    activity_type = find_field(
        soup,
        "Activity type"
    )

    participant_countries = find_field(
        soup,
        "Looking for participants from"
    )

    deadline = find_field(
        soup,
        "Deadline for applications"
    )

    # -----------------------------
    # CLEAN LOCATION
    # -----------------------------

    location_match = re.search(
        r"Activity location\s+(.+?)(?=\s+Activity type\b)",
        text,
        re.IGNORECASE
    )

    if location_match:

        location = clean(
            location_match.group(1)
        )

    # -----------------------------
    # CLEAN PARTICIPANT COUNTRIES
    # -----------------------------

    countries_match = re.search(
        r"Looking for participants from\s+(.+?)(?=\s+Activity topics\b|\s+Deadline for applications\b|\s+Project code\b)",
        text,
        re.IGNORECASE
    )

    if countries_match:

        participant_countries = clean(
            countries_match.group(1)
        )

    # -----------------------------
    # CLEAN DEADLINE
    # -----------------------------

    deadline_match_text = re.search(
        r"Deadline for applications\s+"
        r"Application deadline:\s*"
        r"(\d{2}/\d{2}/\d{4})"
        r"(?:\s+(\d{2}:\d{2}))?",
        text,
        re.IGNORECASE
    )

    if deadline_match_text:

        date_part = (
            deadline_match_text.group(1)
        )

        time_part = (
            deadline_match_text.group(2)
            or "23:59"
        )

        deadline = (
            f"{date_part} {time_part}"
        )

    else:

        deadline_match = re.search(
            r"(\d{2}/\d{2}/\d{4})"
            r"(?:\s+(\d{2}:\d{2}))?",
            deadline
        )

        if deadline_match:

            deadline = (
                f"{deadline_match.group(1)} "
                f"{deadline_match.group(2) or '23:59'}"
            )

    # -----------------------------
    # PROJECT CODE
    # -----------------------------

    project_code = ""

    project_match = re.search(
        r"Project code\s*"
        r"([A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-"
        r"[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+)",
        text,
        re.IGNORECASE
    )

    if project_match:

        project_code = clean(
            project_match.group(1)
        )

    # -----------------------------
    # ORGANISATION
    # -----------------------------

    organisation = ""

    organisation_match = re.search(
        r"(?:Organisation|Organization)\s+"
        r"(.+?)(?=\s+(?:Activity dates|"
        r"Activity location|Activity type|"
        r"Looking for participants|"
        r"Deadline|Project code))",
        text,
        re.IGNORECASE
    )

    if organisation_match:

        organisation = clean(
            organisation_match.group(1)
        )

    # -----------------------------
    # DESCRIPTION
    # -----------------------------

    description = ""

    description_match = re.search(
        r"Description\s+(.+?)(?=\s+Participant profile\b)",
        text,
        re.IGNORECASE
    )

    if description_match:

        description = clean(
            description_match.group(1)
        )

    # -----------------------------
    # PARTICIPANT PROFILE
    # -----------------------------

    profile = ""

    profile_match = re.search(
        r"Participant profile\s+(.+?)(?=\s+(?:Activity dates|"
        r"Activity location|Activity type|"
        r"Looking for participants|"
        r"Deadline for applications|"
        r"Project code)\b)",
        text,
        re.IGNORECASE
    )

    if profile_match:

        profile = clean(
            profile_match.group(1)
        )

    # -----------------------------
    # ALGERIA
    # -----------------------------

    countries_lower = (
        participant_countries.lower()
    )

    if "algeria" in countries_lower:

        algeria_status = "ELIGIBLE"

    elif participant_countries:

        algeria_status = "NOT_LISTED"

    else:

        algeria_status = "UNKNOWN"

    # -----------------------------
    # DEADLINE STATUS
    # -----------------------------

    status = "OPEN"

    date_check = re.search(
        r"(\d{2}/\d{2}/\d{4})"
        r"(?:\s+(\d{2}:\d{2}))?",
        deadline
    )

    if date_check:

        date_part = (
            date_check.group(1)
        )

        time_part = (
            date_check.group(2)
            or "23:59"
        )

        try:

            deadline_dt = datetime.strptime(
                f"{date_part} {time_part}",
                "%d/%m/%Y %H:%M"
            ).replace(
                tzinfo=timezone.utc
            )

            if deadline_dt < datetime.now(
                timezone.utc
            ):

                status = "EXPIRED"

        except ValueError:

            status = "OPEN"

    # -----------------------------
    # BENEFITS
    # -----------------------------

    def detect_yes(
        source_text,
        keywords
    ):

        source_text = clean(
            source_text
        ).lower()

        for keyword in keywords:

            if keyword.lower() in source_text:

                return "YES"

        return "UNKNOWN"

    housing = detect_yes(
        text,
        [
            "accommodation",
            "housing",
            "provided accommodation",
            "free accommodation"
        ]
    )

    food = detect_yes(
        text,
        [
            "food",
            "meals",
            "food allowance",
            "meal allowance"
        ]
    )

    travel = detect_yes(
        text,
        [
            "travel",
            "travel costs",
            "travel expenses",
            "travel reimbursement"
        ]
    )

    pocket_money = detect_yes(
        text,
        [
            "pocket money",
            "pocket allowance",
            "monthly allowance",
            "allowance"
        ]
    )

    # -----------------------------
    # AGE
    # -----------------------------

    age = ""

    age_patterns = [

        r"age\s*(?:range)?\s*:?\s*"
        r"(\d{1,2})\s*[-–]\s*(\d{1,2})",

        r"(\d{1,2})\s*[-–]\s*"
        r"(\d{1,2})\s*years old",

        r"between\s+(\d{1,2})"
        r"\s+and\s+(\d{1,2})"

    ]

    for pattern in age_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            age = (
                f"{match.group(1)}-"
                f"{match.group(2)}"
            )

            break

    # -----------------------------
    # RESULT
    # -----------------------------

    item = {

        "url":
            url,

        "title":
            title,

        "organisation":
            organisation,

        "description":
            description,

        "profile":
            profile,

        "activity_dates":
            activity_dates,

        "location":
            location,

        "activity_type":
            activity_type,

        "participant_countries":
            participant_countries,

        "deadline":
            deadline,

        "project_code":
            project_code,

        "algeria_status":
            algeria_status,

        "status":
            status,

        "age":
            age,

        "housing":
            housing,

        "food":
            food,

        "travel":
            travel,

        "pocket_money":
            pocket_money
    }

    # -----------------------------
    # DIGEST
    # -----------------------------

    digest = hashlib.sha256(
        repr(
            sorted(
                item.items()
            )
        ).encode("utf-8")
    ).hexdigest()

    return item, digest
from threading import Lock

_worker_lock = Lock()


def fetch_extract_worker(url, max_attempts=3):
    """
    Fetch + extract one opportunity using an independent
    Playwright browser/context.

    Designed for controlled parallel workers.
    """

    from playwright.sync_api import sync_playwright

    for attempt in range(1, max_attempts + 1):

        print(
            f"[Worker] {url} "
            f"(attempt {attempt}/{max_attempts})"
        )

        pw = None
        browser = None
        context = None
        page = None

        try:

            pw = sync_playwright().start()

            browser = pw.chromium.launch(
                headless=True
            )

            context = browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 900
                },
                user_agent=HEADERS["User-Agent"],
                locale="en-US"
            )

            page = context.new_page()

            page.set_default_timeout(
                30000
            )

            page.set_default_navigation_timeout(
                60000
            )

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            if response:

                status = response.status

                if status == 429:

                    print(
                        "[429] Waiting..."
                    )

                    wait_time = min(
                        2 ** attempt,
                        15
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                if status >= 500:

                    print(
                        "[HTTP]",
                        status,
                        "Waiting..."
                    )

                    time.sleep(
                        min(
                            2 ** attempt,
                            15
                        )
                    )

                    continue

            page.wait_for_timeout(
                500
            )

            html = page.content()

            item, digest = extract(
                url,
                html
            )

            return item, digest

        except Exception as error:

            print(
                f"[Retry] {attempt}/{max_attempts} | "
                f"{type(error).__name__}: {error}"
            )

            if attempt < max_attempts:

                time.sleep(
                    min(
                        2 ** attempt,
                        15
                    )
                )

        finally:

            try:

                if page:
                    page.close()

            except Exception:
                pass

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

            try:

                if pw:
                    pw.stop()

            except Exception:
                pass

    return None, None