
from flask import Flask, render_template, redirect, request, url_for, send_file, Response
import json, os, sqlite3, datetime, csv, io, qrcode

APP_TITLE = "Reunidas | Vagas e Documentos"
CONFIG_FILE = os.environ.get("PORTAL_CONFIG", "config.json")
DB_FILE = os.environ.get("PORTAL_DB", "clicks.db")

app = Flask(__name__)

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS clicks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            slug TEXT,
            url TEXT,
            bus TEXT,
            ua TEXT,
            ip TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, job_slug TEXT, nome TEXT, email TEXT, telefone TEXT, obs TEXT,
            resume_path TEXT, bus TEXT, ip TEXT, ua TEXT
        )
    """)
    return con

@app.context_processor
def inject_globals():
    cfg = load_config()
    return dict(app_title=APP_TITLE, brand=cfg.get("brand", {}))

@app.route("/")
def index():
    cfg = load_config()
    bus = request.args.get("bus", "").strip()
    groups = cfg.get("groups", [])
    return render_template("index.html", groups=groups, bus=bus)

@app.route("/vagas")
def vagas():
    cfg = load_config()
    jobs = cfg.get("jobs", [])
    bus = request.args.get("bus", "").strip()
    return render_template("jobs.html", jobs=jobs, bus=bus)

@app.route("/vaga/<slug>", methods=["GET","POST"])
def vaga(slug):
    cfg = load_config()
    job = next((j for j in cfg.get("jobs", []) if j.get("slug")==slug), None)
    if not job:
        return redirect(url_for("vagas"))
    bus = request.args.get("bus", "").strip()
    if request.method == "POST":
        nome = request.form.get("nome","").strip()
        email = request.form.get("email","").strip()
        telefone = request.form.get("telefone","").strip()
        obs = request.form.get("obs","").strip()
        file = request.files.get("curriculo")
        resume_path = None
        if file and file.filename:
            safe_name = f"{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{slug}_{file.filename.replace(' ','_')}"
            updir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(updir, exist_ok=True)
            dest = os.path.join(updir, safe_name)
            file.save(dest)
            resume_path = dest
        con = db()
        con.execute("""
            INSERT INTO applications(ts, job_slug, nome, email, telefone, obs, resume_path, bus, ip, ua)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (datetime.datetime.utcnow().isoformat(), slug, nome, email, telefone, obs, resume_path, bus,
              request.headers.get("X-Forwarded-For", request.remote_addr), request.headers.get("User-Agent","")))
        con.commit(); con.close()
        return render_template("thanks.html", job=job, bus=bus)
    return render_template("job_detail.html", job=job, bus=bus)

@app.route("/r/<slug>")
def go(slug):
    cfg = load_config()
    target_url = None
    for g in cfg.get("groups", []):
        for item in g.get("items", []):
            if item.get("slug") == slug:
                target_url = item.get("url")
                break
        if target_url: break
    if not target_url:
        return redirect(url_for("index"))
    con = db()
    con.execute("INSERT INTO clicks(ts, slug, url, bus, ua, ip) VALUES(?,?,?,?,?,?)",
                (datetime.datetime.utcnow().isoformat(), slug, target_url, request.args.get("bus",""),
                 request.headers.get("User-Agent",""), request.headers.get("X-Forwarded-For", request.remote_addr)))
    con.commit(); con.close()
    return redirect(target_url)

@app.route("/qr/<slug>.png")
def qr(slug):
    base = request.url_root.rstrip("/")
    bus = request.args.get("bus", "")
    qr_url = f"{base}/r/{slug}"
    if bus: qr_url += f"?bus={bus}"
    img = qrcode.make(qr_url)
    bio = io.BytesIO(); img.save(bio, format="PNG"); bio.seek(0)
    return send_file(bio, mimetype="image/png")

@app.route("/admin")
def admin():
    token_req = os.environ.get("ADMIN_TOKEN")
    if token_req and request.args.get("k") != token_req:
        return "Não autorizado. Acrescente ?k=SEU_TOKEN", 401
    con = db(); cur = con.cursor()
    cur.execute("SELECT slug, COUNT(*), MIN(ts), MAX(ts) FROM clicks GROUP BY slug ORDER BY COUNT(*) DESC")
    rows_clicks = cur.fetchall()
    cur.execute("SELECT job_slug, COUNT(*) FROM applications GROUP BY job_slug ORDER BY COUNT(*) DESC")
    rows_jobs = cur.fetchall()
    con.close()
    return render_template("admin.html", rows_clicks=rows_clicks, rows_jobs=rows_jobs)

@app.route("/export.csv")
def export_csv():
    token_req = os.environ.get("ADMIN_TOKEN")
    if token_req and request.args.get("k") != token_req:
        return "Não autorizado.", 401
    con = db(); cur = con.cursor()
    cur.execute("SELECT ts, slug, url, bus, ua, ip FROM clicks ORDER BY ts DESC")
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["ts_utc","slug","url","bus","user_agent","ip"])
    writer.writerows(cur.fetchall()); con.close()
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=cliques.csv"})

@app.route("/candidatos.csv")
def export_candidatos():
    token_req = os.environ.get("ADMIN_TOKEN")
    if token_req and request.args.get("k") != token_req:
        return "Não autorizado.", 401
    con = db(); cur = con.cursor()
    cur.execute("SELECT ts, job_slug, nome, email, telefone, obs, resume_path, bus, ip, ua FROM applications ORDER BY ts DESC")
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["ts_utc","job_slug","nome","email","telefone","obs","arquivo","bus","ip","ua"])
    writer.writerows(cur.fetchall()); con.close()
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=candidatos.csv"})

if __name__ == "__main__":
    db().close()
    app.run(host="0.0.0.0", port=8000, debug=True)
