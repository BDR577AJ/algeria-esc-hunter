import os, requests

def send(text):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[Telegram disabled]\n"+text); return
    r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id":chat,"text":text},timeout=20)
    r.raise_for_status()

def message(item,state):
    return (f"🇩🇿 {state}\n{item['title']}\n"
            f"⭐ Match: {item['match_score']}/100\n"
            f"📍 {item['location']}\n📅 {item['activity_dates']}\n"
            f"⏰ {item['deadline'] or 'No application deadline'}\n"
            f"🧾 {item['project_code']}\n🔗 {item['url']}")
