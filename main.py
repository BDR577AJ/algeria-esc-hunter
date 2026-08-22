import os,time
from dotenv import load_dotenv
from crawler import fetch,extract
from discovery import discover
from analyzer import analyze
from database import upsert
from telegram import send,message

load_dotenv()

def seeds():
    try:
        return [x.strip() for x in open("seed_urls.txt",encoding="utf-8")
                if x.strip() and not x.startswith("#")]
    except FileNotFoundError: return []

def run_once():
    urls=set(seeds())
    try: urls.update(discover())
    except Exception as e: print("Discovery error:",e)
    print("Candidates:",len(urls))
    delay=float(os.getenv("REQUEST_DELAY_SECONDS","2"))
    for url in sorted(urls):
        try:
            item,digest=extract(url,fetch(url,delay))
            item=analyze(item)
            state=upsert(item,digest)
            print(state,item["algeria_status"],item["match_score"],item["title"])
            if state in ("NEW","UPDATED") and item["algeria_status"]=="ELIGIBLE" and item["status"]!="EXPIRED":
                send(message(item,state))
        except Exception as e: print("ERROR",url,repr(e))

if __name__=="__main__":
    while True:
        run_once()
        time.sleep(int(os.getenv("CHECK_INTERVAL_MINUTES","60"))*60)
