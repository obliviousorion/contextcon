"""Local, dependency-free HTTP adapter for the FreightClose demo."""
import argparse
import json
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import service


INDEX = Path(__file__).with_name("index.html")
CASE_ROUTE = re.compile(r"/api/cases/([A-Za-z0-9_-]{1,80})/(resolve|retry|receipt)")
MAX_BODY = 32 * 1024


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, status, content_type, body, filename=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, value, filename=None):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_bytes(status, "application/json; charset=utf-8", body, filename)

    def read_json(self):
        if self.headers.get_content_type() != "application/json":
            raise service.ServiceError(415, "Use an application/json request body")
        length = self.headers.get("Content-Length", "")
        if not length.isascii() or not length.isdigit() or len(length) > 9:
            raise service.ServiceError(400, "Supply a valid Content-Length header")
        if int(length) > MAX_BODY:
            raise service.ServiceError(413, "Request exceeds 32 KiB")
        try:
            value = json.loads(self.rfile.read(int(length)).decode("utf-8"))
        except (ValueError, RecursionError):
            raise service.ServiceError(400, "Request body must be valid UTF-8 JSON") from None
        if not isinstance(value, dict):
            raise service.ServiceError(422, "Expected a JSON object")
        return value

    def dispatch(self):
        url = urlsplit(self.path)
        case = CASE_ROUTE.fullmatch(url.path)
        if self.command == "GET":
            if url.path == "/":
                return self.send_bytes(200, "text/html; charset=utf-8", INDEX.read_bytes())
            if url.path == "/api/sample":
                missing = parse_qs(url.query).get("missing", ["false"])[0].lower()
                if missing not in ("false", "true", "0", "1"):
                    raise service.ServiceError(422, "missing must be true or false")
                return self.send_json(200, service.get_sample(missing in ("true", "1")))
            if url.path == "/api/cases":
                return self.send_json(200, service.history())
            if url.path == "/api/status":
                return self.send_json(200, service.status())
            if case and case[2] == "receipt":
                return self.send_json(200, service.receipt_data(case[1]), f"freight-{case[1]}.json")
        if self.command == "POST":
            if url.path == "/api/run":
                return self.send_json(200, service.run(self.read_json()))
            if case and case[2] == "resolve":
                return self.send_json(200, service.resolve(case[1], self.read_json()))
            if case and case[2] == "retry":
                if self.headers.get("Content-Length", "0") != "0":
                    self.read_json()
                return self.send_json(200, service.retry(case[1]))
        raise service.ServiceError(404, "Unknown endpoint")

    def do_GET(self):
        try:
            self.dispatch()
        except service.ServiceError as error:
            self.send_json(error.status_code, {"detail": error.detail})
        except (ConnectionError, TimeoutError):
            self.close_connection = True
        except Exception as error:
            self.log_error("Service failure: %s", type(error).__name__)
            self.send_json(500, {"detail": "Service failed while processing this request"})

    do_POST = do_GET


def clear_sandbox():
    """Delete the sandbox database so a rehearsal starts from zero cases and postings."""
    path = Path(service.db_path())
    if path.suffix != ".sqlite3":
        raise SystemExit(f"--fresh only deletes *.sqlite3 sandbox files, not {path}")
    removed = [p for p in (path, *(Path(f"{path}{s}") for s in ("-journal", "-wal", "-shm")))
               if p.exists()]
    for p in removed:
        p.unlink()
    print(f"Fresh sandbox: {path.name} {'cleared' if removed else 'was already empty'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--fresh", action="store_true",
                        help="delete this mode's sandbox database before serving")
    args = parser.parse_args()
    if args.fresh:
        clear_sandbox()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        sources = f"invoice reader: {service.MODE}, FX: {service.FX_MODE}"
        print(f"FreightClose running at {url} ({sources})", flush=True)
        if args.open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
