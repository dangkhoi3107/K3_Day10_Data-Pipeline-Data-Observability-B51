"""HTTP Server for Data Pipeline & Data Observability Web UI Dashboard."""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import sys

src_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(src_dir))

from core.config import load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question
from pipelines.phase1 import main as run_phase1_pipeline
from pipelines.corruption_flow import main as run_corruption_pipeline

UI_DIR = Path(__file__).resolve().parent

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/status":
            self._handle_get_status()
        elif self.path == "/api/report":
            self._handle_get_report()
        elif self.path == "/" or not self.path.startswith("/api"):
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        data = json.loads(body) if body else {}

        if self.path == "/api/query":
            self._handle_query(data)
        elif self.path == "/api/run-phase1":
            self._handle_run_phase1()
        elif self.path == "/api/run-corruption":
            self._handle_run_corruption()
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_get_status(self):
        settings = load_settings()
        def safe_read(p):
            return read_json(p) if p.exists() else {}

        baseline_metrics = safe_read(settings.paths.baseline_metrics)
        corrupted_metrics = safe_read(settings.paths.corrupted_metrics)
        repaired_metrics = safe_read(settings.paths.repaired_metrics)

        baseline_quality = safe_read(settings.paths.quality_dir / "baseline_quality.json")
        corrupted_quality = safe_read(settings.paths.quality_dir / "corrupted_quality.json")
        repaired_quality = safe_read(settings.paths.quality_dir / "repaired_quality.json")

        corrupted_freshness = safe_read(settings.paths.quality_dir / "corrupted_freshness.json")
        repaired_freshness = safe_read(settings.paths.quality_dir / "repaired_freshness.json")

        corruption_log = safe_read(settings.paths.corruption_log)

        response = {
            "metrics": {
                "baseline": baseline_metrics,
                "corrupted": corrupted_metrics,
                "repaired": repaired_metrics,
            },
            "quality": {
                "baseline": baseline_quality,
                "corrupted": corrupted_quality,
                "repaired": repaired_quality,
            },
            "freshness": {
                "corrupted": corrupted_freshness,
                "repaired": repaired_freshness,
            },
            "corruption_log": corruption_log,
        }
        self._send_json(response)

    def _handle_get_report(self):
        settings = load_settings()
        report_p = settings.paths.comparison_report
        content = report_p.read_text(encoding="utf-8") if report_p.exists() else "No report generated yet."
        self._send_json({"content": content})

    def _handle_query(self, data):
        question = data.get("question", "").strip()
        if not question:
            self._send_json({"error": "Question is required"}, status=400)
            return

        settings = load_settings()
        if not settings.paths.embeddings_json.exists():
            self._send_json({"error": "Vector index not found. Please run Phase 1 baseline first."}, status=400)
            return

        index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
        result = answer_question(question, settings=settings, index=index)
        self._send_json({
            "question": result.question,
            "answer": result.answer,
            "retrieved_doc_ids": result.retrieved_doc_ids,
            "retrieved_titles": result.retrieved_titles,
            "retrieved_contexts": result.retrieved_contexts,
        })

    def _handle_run_phase1(self):
        try:
            run_phase1_pipeline()
            self._send_json({"message": "Phase 1 Baseline Pipeline completed successfully!"})
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_run_corruption(self):
        try:
            run_corruption_pipeline()
            self._send_json({"message": "Phase 2 Corruption & Repair Flow completed successfully!"})
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)


def start_server(port=8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"🚀 Data Observability Dashboard UI running at: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    start_server(port)
