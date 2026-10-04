# server.py
# Web wrapper cho spamsmsv1.py — KHÔNG sửa file gốc
import os
import asyncio
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

# Import các hàm từ file gốc
import spamsmsv1 as core

API_KEY = os.environ.get("API_KEY", "").strip()
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def render(template_name, **ctx):
    tpl = env.get_template(template_name)
    return web.Response(text=tpl.render(**ctx), content_type="text/html")


def check_api_key(request):
    if not API_KEY:
        return True
    key = request.headers.get("X-API-Key") or request.query.get("key", "")
    return key == API_KEY


async def handle_index(request):
    key = request.query.get("key", "")
    authed = (not API_KEY) or (key == API_KEY)
    return render("index.html", authed=authed, api_key_set=bool(API_KEY))


async def handle_sms(request):
    if not check_api_key(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    raw_numbers = data.get("numbers", "").strip()
    threads = int(data.get("threads", 10))
    if not raw_numbers:
        return web.json_response({"error": "Thiếu danh sách số"}, status=400)

    # Tách số và chuẩn hóa
    numbers = []
    for line in raw_numbers.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            numbers.append(core.normalize_phone(line))
        except Exception:
            pass

    if not numbers:
        return web.json_response({"error": "Không có số hợp lệ"}, status=400)

    # Chạy trong thread riêng để không block event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, core.start_sms_bombing, numbers, threads)

    return web.json_response({"success": True, "count": len(numbers), "type": "sms"})


async def handle_call(request):
    if not check_api_key(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    raw_numbers = data.get("numbers", "").strip()
    threads = int(data.get("threads", 5))
    if not raw_numbers:
        return web.json_response({"error": "Thiếu danh sách số"}, status=400)

    numbers = []
    for line in raw_numbers.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            numbers.append(core.normalize_phone(line))
        except Exception:
            pass

    if not numbers:
        return web.json_response({"error": "Không có số hợp lệ"}, status=400)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, core.start_call_bombing, numbers, threads)

    return web.json_response({"success": True, "count": len(numbers), "type": "call"})


async def handle_health(request):
    return web.Response(text="OK")


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/sms", handle_sms)
    app.router.add_post("/call", handle_call)
    app.router.add_get("/health", handle_health)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(create_app(), host="0.0.0.0", port=port)
