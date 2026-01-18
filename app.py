from flask import Flask, request, jsonify
from pathlib import Path
import tempfile
import os

from web import convert_pdf_to_dataframe

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY", "dev-key")  # set on Render

@app.route("/api/convert", methods=["POST"])
def convert_api():
    # Security
    if request.headers.get("X-API-KEY") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / file.filename
        file.save(pdf_path)

        df = convert_pdf_to_dataframe(pdf_path)

        if df is None or df.empty:
            return jsonify({"error": "Conversion failed"}), 500

        return jsonify({
            "status": "success",
            "rows": df.values.tolist()
        })

if __name__ == "__main__":
    app.run()
