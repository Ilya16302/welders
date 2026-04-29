from flask import Flask, jsonify, send_from_directory, request
import json, os, zipfile

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def get_path(name):
    return os.path.join(DATA_DIR, name)

def ensure_split():
    zip_path = get_path("db.zip")
    json_path = get_path("db.json")
    welders_path = get_path("welders.json")
    joints_path = get_path("joints.json")

    if os.path.exists(zip_path):
        if not os.path.exists(json_path) or os.path.getmtime(zip_path) > os.path.getmtime(json_path):
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extract("db.json", DATA_DIR)

    if os.path.exists(json_path):
        if not os.path.exists(welders_path) or os.path.getmtime(json_path) > os.path.getmtime(welders_path):
            with open(json_path, encoding="utf-8") as f:
                db = json.load(f)
            with open(welders_path, "w", encoding="utf-8") as f:
                json.dump({"updated_at": db["updated_at"], "period_start": db.get("period_start",""), "period_end": db.get("period_end",""), "welders": db["welders"], "stats": db["stats"]}, f, ensure_ascii=False)
            with open(joints_path, "w", encoding="utf-8") as f:
                json.dump(db["joints"], f, ensure_ascii=False)

def load_welders():
    ensure_split()
    with open(get_path("welders.json"), encoding="utf-8") as f:
        return json.load(f)

def load_joints():
    with open(get_path("joints.json"), encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/api/welders")
def api_welders():
    data = load_welders()
    stats = data.get("stats", {})
    welders = []
    for w in data.get("welders", []):
        s = stats.get(w["fio"], {})
        welders.append({**w, "total": s.get("total",0), "good": s.get("good",0), "bad": s.get("bad",0), "pct_bad": s.get("pct_bad"), "good_period": s.get("good_period",0), "bad_period": s.get("bad_period",0), "pct_bad_period": s.get("pct_bad_period"), "status": s.get("status","")})
    return jsonify({"updated_at": data.get("updated_at"), "period_start": data.get("period_start"), "period_end": data.get("period_end"), "welders": welders})

@app.route("/api/welder/<path:fio>")
def api_welder(fio):
    data = load_welders()
    stats = data.get("stats", {}).get(fio, {})
    joints = [j for j in load_joints() if any(h.get("welder") == fio for h in j.get("history", []))]
    return jsonify({"fio": fio, "stats": stats, "joints": joints, "updated_at": data.get("updated_at"), "period_start": data.get("period_start"), "period_end": data.get("period_end")})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
