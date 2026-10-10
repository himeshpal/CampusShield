"""Fake IP camera: HTTP admin page on 80 and an RTSP responder on 554."""
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class Web(BaseHTTPRequestHandler):
    server_version = "IPCam-Webs/2.0"
    sys_version = ""

    def do_GET(self):
        body = b"<html><head><title>IP Camera - Main Gate</title></head><body><h1>Network Camera</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Rtsp(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024).decode(errors="ignore")
        cseq = next((l.split(":")[1].strip() for l in data.splitlines() if l.lower().startswith("cseq")), "1")
        self.request.sendall(
            f"RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\nServer: IPCam RTSP Server 1.0\r\n"
            "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n\r\n".encode()
        )


socketserver.ThreadingTCPServer.allow_reuse_address = True
threading.Thread(target=socketserver.ThreadingTCPServer(("", 554), Rtsp).serve_forever, daemon=True).start()
HTTPServer(("", 80), Web).serve_forever()
