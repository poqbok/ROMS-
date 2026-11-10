#!/usr/bin/env python3
"""ROMS 수치예측모델 조회 사이트 서버 (외부 패키지 불필요, Python 3.8+).

- GET /            -> index.html
- GET /api/roms    -> 공공데이터포털 ROMS API 프록시 (인증키는 서버 환경변수 ROMS_API_KEY)
- GET /healthz     -> 상태 확인
"""
import json, os, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote, unquote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def _load_env():
    """같은 폴더의 .env 파일(KEY=VALUE)을 읽어 환경변수로 등록 (이미 설정된 값은 유지)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
BASE = os.environ.get("ROMS_BASE_URL", "https://apis.data.go.kr/1192136/roms/GetRomsApiService")
KEY = os.environ.get("ROMS_API_KEY", "").strip()
PORT = int(os.environ.get("PORT", "8000"))
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_SEC = 600
_cache, _lock = {}, threading.Lock()


def num(q, name, lo, hi):
    v = float(q[name][0])
    if not (lo <= v <= hi):
        raise ValueError(f"{name} 범위 오류")
    return v


def build_query(q):
    ymin, ymax = num(q, "ymin", 0, 90), num(q, "ymax", 0, 90)
    xmin, xmax = num(q, "xmin", 0, 180), num(q, "xmax", 0, 180)
    if ymin >= ymax or xmin >= xmax:
        raise ValueError("최소값이 최대값보다 작아야 합니다")
    if ymax - ymin > 1.0001 or xmax - xmin > 1.0001:
        raise ValueError("위도·경도 범위는 각각 최대 1도입니다")
    page = int(num(q, "pageNo", 1, 10000)) if "pageNo" in q else 1
    rows = int(num(q, "numOfRows", 1, 300)) if "numOfRows" in q else 10
    key = KEY if "%" in KEY else quote(KEY, safe="")
    return (f"serviceKey={key}&type=json&ymin={ymin}&ymax={ymax}&xmin={xmin}&xmax={xmax}"
            f"&pageNo={page}&numOfRows={rows}")


def fetch_upstream(query):
    now = time.time()
    with _lock:
        hit = _cache.get(query)
        if hit and now - hit[0] < CACHE_SEC:
            return hit[1]
    req = Request(f"{BASE}?{query}", headers={"Accept": "application/json", "User-Agent": "roms-site/1.0"})
    with urlopen(req, timeout=30) as r:
        body = r.read()
    with _lock:
        if len(_cache) > 300:
            _cache.clear()
        _cache[query] = (now, body)
    return body


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype.startswith("application") else "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code, msg):
        self._send(code, json.dumps({"error": msg}, ensure_ascii=False))

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/healthz":
            return self._send(200, json.dumps({"ok": True, "keyConfigured": bool(KEY)}))
        if u.path == "/api/roms":
            if not KEY:
                return self._err(500, "서버에 ROMS_API_KEY 환경변수가 설정되지 않았습니다.")
            try:
                query = build_query(parse_qs(u.query))
            except (KeyError, ValueError) as e:
                return self._err(400, f"요청값 오류: {e}")
            try:
                return self._send(200, fetch_upstream(query))
            except HTTPError as e:
                return self._err(502, f"공공데이터포털 응답 오류 (HTTP {e.code})")
            except (URLError, TimeoutError):
                return self._err(504, "공공데이터포털에 연결하지 못했습니다.")
        self._err(404, "not found")

    def log_message(self, fmt, *args):
        # 인증키가 로그에 남지 않도록 쿼리는 기록하지 않음
        print("%s %s" % (self.command, urlparse(self.path).path))


if __name__ == "__main__":
    print(f"ROMS site on http://0.0.0.0:{PORT}  (key {'set' if KEY else 'MISSING'})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
