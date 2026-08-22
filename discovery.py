import os
from urllib.parse import urlencode

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


load_dotenv()


DEFAULT_URL = (
    "https://youth.europa.eu/"
    "go-abroad/volunteering/opportunities_en"
)

API_BASE = (
    "https://youth.europa.eu/"
    "api/rest/eyp/v1/search_en"
)


def build_params(size):

    discovery_date = os.getenv(
        "DISCOVERY_DATE",
        "2026-08-22T00:00:00"
    )

    params = [
        ("type", "Opportunity"),
        ("size", str(size)),
        ("from", "0"),

        ("filters[status]", "open"),

        (
            "filters[date_end][operator]",
            ">="
        ),

        (
            "filters[date_end][value]",
            discovery_date
        ),

        (
            "filters[date_end][type]",
            "must"
        ),

        (
            "filters[funding_programme][id][0]",
            "5"
        ),

        (
            "filters[funding_programme][id][1]",
            "4"
        ),

        (
            "filters[funding_programme][id][2]",
            "3"
        ),

        (
            "filters[funding_programme][id][3]",
            "2"
        ),

        (
            "filters[funding_programme][id][4]",
            "1"
        ),

        (
            "filters[funding_programme][id][5]",
            "8"
        ),

        (
            "filters[funding_programme][id][6]",
            "6"
        ),

        (
            "filters[funding_programme][id][7]",
            "7"
        ),

        (
            "filters[date_application_end][operator]",
            ">="
        ),

        (
            "filters[date_application_end][value]",
            discovery_date
        ),

        (
            "filters[date_application_end][type]",
            "must"
        ),

        (
            "filters[date_application_end][group]",
            "deadline"
        ),

        (
            "filters[has_no_deadline][value]",
            "true"
        ),

        (
            "filters[has_no_deadline][type]",
            "must"
        ),

        (
            "filters[has_no_deadline][group]",
            "deadline"
        ),

        ("fields[0]", "opid"),
        ("fields[1]", "title"),
        ("fields[2]", "logo"),
        ("fields[3]", "geocode.lat"),
        ("fields[4]", "geocode.lon"),
        ("fields[5]", "town"),
        ("fields[6]", "country"),
        ("fields[7]", "has_no_deadline"),
        ("fields[8]", "duration"),
        ("fields[9]", "date_start"),
        ("fields[10]", "date_end"),
        ("fields[11]", "date_application_end"),
        ("fields[12]", "is_esc_related"),
        ("fields[13]", "created"),

        ("sort[created]", "desc"),
    ]

    return params


def make_api_url(size):

    return (
        API_BASE
        + "?"
        + urlencode(
            build_params(size)
        )
    )


def request_api(request, size):

    url = make_api_url(size)

    response = request.get(
        url,
        timeout=120000
    )

    print(
        "[Discovery] API request size:",
        size,
        "| status:",
        response.status
    )

    if response.status != 200:

        print(
            "[Discovery] API request failed:",
            response.text[:500]
        )

        return None

    return response.json()


def discover():

    print(
        "[Discovery] Using Youth Portal API"
    )

    with sync_playwright() as p:

        request = p.request.new_context(
            extra_http_headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )

        try:

            # ---------------------------------
            # STEP 1
            # Ask API for the current total.
            # ---------------------------------

            print(
                "[Discovery] Checking current total..."
            )

            data = request_api(
                request,
                1
            )

            if not data:

                return []

            total_data = (
                data
                .get("hits", {})
                .get("total", {})
            )

            total = int(
                total_data.get(
                    "value",
                    0
                )
            )

            print(
                "[Discovery] CURRENT API TOTAL:",
                total
            )

            if total <= 0:

                print(
                    "[Discovery] No opportunities found."
                )

                return []

            # ---------------------------------
            # STEP 2
            # Request the actual current total.
            # ---------------------------------

            print(
                "[Discovery] Requesting:",
                total,
                "opportunities..."
            )

            data = request_api(
                request,
                total
            )

            if not data:

                return []

        finally:

            request.dispose()

    # ---------------------------------
    # READ RESULTS
    # ---------------------------------

    hits = (
        data
        .get("hits", {})
        .get("hits", [])
    )

    returned = len(hits)

    print(
        "[Discovery] Returned records:",
        returned
    )

    # ---------------------------------
    # BUILD URLS
    # ---------------------------------

    urls = set()

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

        urls.add(
            "https://youth.europa.eu/"
            f"solidarity/opportunity/"
            f"{opid}_en"
        )

    result = sorted(
        urls
    )

    print(
        "[Discovery] OPPORTUNITIES FOUND:",
        len(result)
    )

    return result