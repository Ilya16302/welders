from flask import Flask, jsonify, send_from_directory, abort
import json, os, zipfile

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ZIP_PATH = os.path.join(DATA_DIR, "db.zip")
JSON_PATH = os.path.join(DATA_DIR, "db.json")

def ensure_db():
    """Распаковать db.zip → db.json если нужно"""
    if not os.path.exists(JSON_PATH):
        if os.path.exists(ZIP_PATH):
            with zipfile.ZipFile(ZIP_PATH, 'r') as z:
                z.extract("db.json", DATA_DIR)
        else:
            raise FileNotFoundError("Нет ни db.json ни db.zip в папке data/")
    # Если zip новее json — перераспаковать
    elif os.path.exists(ZIP_PATH):
        if os.path.getmtime(ZIP_PATH) > os.path.getmtime(JSON_PATH):
            with zipfile.ZipFile(ZIP_PATH, 'r') as z:
                z.extract("db.json", DATA_DIR)

def load_db():
    ensure_db()
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/api/db/meta")
def api_meta():
    """Только метаданные — быстро"""
    db = load_db()
    return jsonify({
        "updated_at": db.get("updated_at"),
        "period_start": db.get("period_start"),
        "period_end": db.get("period_end"),
        "welders_count": len(db.get("welders", [])),
        "joints_count": len(db.get("joints", [])),
    })

@app.route("/api/welders")
def api_welders():
    db = load_db()
    # Обогащаем список сварщиков базовой статистикой
    stats = db.get("stats", {})
    welders = []
    for w in db.get("welders", []):
        s = stats.get(w["fio"], {})
        welders.append({
            **w,
            "total": s.get("total", 0),
            "good": s.get("good", 0),
            "bad": s.get("bad", 0),
            "pct_bad": s.get("pct_bad"),
            "good_period": s.get("good_period", 0),
            "bad_period": s.get("bad_period", 0),
            "pct_bad_period": s.get("pct_bad_period"),
            "status": s.get("status", ""),
        })
    return jsonify({
        "updated_at": db.get("updated_at"),
        "welders": welders
    })

@app.route("/api/welder/<path:fio>")
def api_welder(fio):
    db = load_db()
    stats = db.get("stats", {}).get(fio, {})
    joints = [j for j in db.get("joints", [])
              if any(h.get("welder") == fio for h in j.get("history", []))]
    return jsonify({
        "fio": fio,
        "stats": stats,
        "joints": joints,
        "updated_at": db.get("updated_at"),
        "period_start": db.get("period_start"),
        "period_end": db.get("period_end"),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
