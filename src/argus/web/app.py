"""Serve the built workbench and its preview API from one origin."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware

from argus.web.api import router


WEB_DIST_DIR = Path(__file__).resolve().parents[2] / "web" / "dist"
app = FastAPI(title="Argus 模型工作台")
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.include_router(router)


@app.api_route("/api", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/api/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def api_not_found(path: str = "") -> None:
    raise HTTPException(404, detail=f"API route not found: /api/{path}")


if not (WEB_DIST_DIR / "index.html").is_file():
    raise RuntimeError("缺少前端构建产物，请执行 pnpm --dir src/web run build。")

app.frontend("/", directory=WEB_DIST_DIR, fallback="index.html", check_dir=True)
