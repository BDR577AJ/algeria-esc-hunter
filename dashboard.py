from flask import Flask,render_template,request
from database import list_open,stats,connect

app=Flask(__name__)

@app.route("/")
def index():
    q=request.args.get("q","").strip().lower()
    rows=list(list_open(500))
    if q:
        rows=[r for r in rows if q in (r["title"] or "").lower() or q in (r["location"] or "").lower()]
    return render_template("dashboard.html",rows=rows,stats=stats(),q=q)

@app.route("/health")
def health(): return {"status":"ok"}

if __name__=="__main__":
    import os
    app.run(host=os.getenv("DASHBOARD_HOST","127.0.0.1"),
            port=int(os.getenv("DASHBOARD_PORT","5000")))
