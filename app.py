# app.py
import os
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify

from web import convert_pdfs_to_json  # <-- we return ALL 3 tabs as JSON

app = Flask(__name__)

def get_api_key():
    # Render env var should be API_KEY. We'll also accept "api" just in case.
    return (os.environ.get("API_KEY") or os.environ.get("api") or "").strip()

@app.route("/", methods=["GET"])
def health():
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

    if not api_key:
        return jsonify({"error": "Server API_KEY not configured"}), 500

    if sent_key != api_key:
        return jsonify({
            "error": "Unauthorized",
            "debug": {
                "header_present": "X-API-KEY" in request.headers,
                "sent_key_length": len(sent_key),
                "server_key_length": len(api_key),
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

        result = convert_pdfs_to_json([pdf_path])
        if not result or result.get("status") != "success":
            return jsonify({"error": "Conversion failed"}), 500

        return jsonify(result), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
