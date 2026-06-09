import json
import os
import queue
import threading
import uuid

from dotenv import load_dotenv
from flask import Flask, Response, request, send_file, stream_with_context

from ai_pipeline import AIPipeline
from docx_builder import build_ebook_docx, build_value_enhancer_docx

load_dotenv()

app = Flask(__name__, static_folder="static")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    keyword = data.get("keyword", "").strip()
    if not keyword:
        return {"error": "keyword is required"}, 400

    session_id = uuid.uuid4().hex[:8]

    def stream():
        event_queue = queue.Queue()

        def run():
            pipeline = AIPipeline()
            try:
                event_queue.put(("step", {"step": 0, "message": "Researching pain points..."}))
                pains = pipeline.brainstorm_pains(keyword)

                event_queue.put(("step", {"step": 1, "message": "Generating solutions..."}))
                pipeline.generate_solutions(keyword, pains)

                event_queue.put(("step", {"step": 2, "message": "Crafting $100M offer..."}))
                offer = pipeline.create_offer(keyword, pains)

                event_queue.put(("step", {"step": 3, "message": "Creating ebook title..."}))
                title_data = pipeline.create_title(offer)
                title = title_data["selectedTitle"]

                event_queue.put(("step", {"step": 4, "message": f'Building outline for "{title}"...'}))
                outline = pipeline.build_outline(title, keyword)

                event_queue.put(("step", {"step": 5, "message": "Generating cover image..."}))
                cover_bytes = pipeline.generate_cover(title, keyword)

                event_queue.put(("step", {"step": 6, "message": "Writing full ebook..."}))
                ebook_content = pipeline.write_ebook(title, keyword, outline)

                event_queue.put(("step", {"step": 7, "message": "Creating value enhancer package..."}))
                value_data = pipeline.create_value_enhancer(title, keyword, offer)

                event_queue.put(("step", {"step": 8, "message": "Building ebook DOCX..."}))
                ebook_file = f"ebook_{session_id}.docx"
                build_ebook_docx(title, ebook_content, cover_bytes, os.path.join(OUTPUT_DIR, ebook_file))

                event_queue.put(("step", {"step": 9, "message": "Building value enhancer DOCX..."}))
                value_file = f"value_enhancer_{session_id}.docx"
                build_value_enhancer_docx(value_data, os.path.join(OUTPUT_DIR, value_file))

                event_queue.put(("done", {
                    "title": title,
                    "ebook_url": f"/download/{ebook_file}",
                    "value_url": f"/download/{value_file}",
                }))
            except Exception as exc:
                event_queue.put(("error", {"message": str(exc)}))
            finally:
                event_queue.put(None)

        threading.Thread(target=run, daemon=True).start()

        while True:
            try:
                item = event_queue.get(timeout=5)
                if item is None:
                    break
                kind, payload = item
                yield f"data: {json.dumps({'event': kind, **payload})}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/download/<filename>")
def download(filename):
    if os.sep in filename or filename.startswith(".") or ".." in filename:
        return {"error": "invalid filename"}, 400
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        return {"error": "file not found"}, 404
    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
