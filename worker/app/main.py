import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import sleep
from urllib.parse import urlparse

import redis


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if urlparse(self.path).path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> None:
    port = int(os.environ.get("WORKER_HEALTH_PORT", "8081"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()

    client = redis.Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=5)
    while True:
        try:
            client.ping()
        except redis.RedisError as exc:
            print(f"Redis is temporarily unavailable: {exc}", flush=True)
        sleep(30)


if __name__ == "__main__":
    main()
