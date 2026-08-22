import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_opportunity(
    title,
    location,
    deadline,
    url
):

    message = (
        "🇩🇿 ESC Opportunity\n\n"
        f"📌 {title}\n"
        f"📍 {location}\n"
        f"📅 Deadline: {deadline}\n\n"
        f"🔗 Apply:\n{url}"
    )

    api = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )

    response = requests.post(
        api,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    print(
        "STATUS:",
        response.status_code
    )

    print(
        response.text
    )


if __name__ == "__main__":

    send_opportunity(
        title="TEST ESC Opportunity",
        location="Romania",
        deadline="15/09/2026",
        url=(
            "https://youth.europa.eu/"
            "solidarity/opportunity/53936_en"
        ),
    )