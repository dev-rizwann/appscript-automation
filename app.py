from flask import Flask, request, jsonify
from pathlib import Path
import tempfile
import os

from web import convert_pdf_to_dataframe

app = Flask(__name__)

def get_api_key():
    # Prefer Render env var API_KEY; fallback to "api" just in case.
    # Strip whitespace to avoid invisible mismatch.
    return (os.environ.get("API_KEY") or os.environ.get("api") or "").strip()

@app.route("/", methods=["GET"])
def health():
    # Helps confirm env var is loaded (without exposing it)
    k = get_api_key()
    return jsonify({
        "status": "ok",
        "has_api_key": bool(k),
        "api_key_length": len(k)
    })

@app.route("/api/convert", methods=["POST"])
def convert_api():
    api_key = get_api_key()
    sent_key = (request.headers.get("X-API-KEY") or "").strip()

    # If the server key is missing, make it obvious in Render logs.
    if not api_key:
        return jsonify({"error": "Server API_KEY not configured"}), 500

    # Debug info without leaking secrets
    if sent_key != api_key:
        return jsonify({
            "error": "Unauthorized",
            "debug": {
                "sent_key_length": len(sent_key),
                "server_key_length": len(api_key),
                "header_present": "X-API-KEY" in request.headers
            }
        }), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / file.filename
        file.save(pdf_path)

        df = convert_pdf_to_dataframe(pdf_path)

        if df is None or df.empty:
            return jsonify({"error": "Conversion failed / no rows extracted"}), 500

        return jsonify({
            "status": "success",
            "columns": list(df.columns),
            "rows": df.values.tolist()
        })

if __name__ == "__main__":
    # Render uses gunicorn; this is only for local testing
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
