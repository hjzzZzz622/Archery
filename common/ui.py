# -*- coding: UTF-8 -*-

from pathlib import Path

from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET


@require_GET
def index(request):
    """
    方案 A：新旧并存
    - /dashboard/ 仍是 Django 模板版
    - /ui/*      是 Vue SPA，新路由统一回退到同一个 index.html

    注意：Vue 构建产物由 `ui/` 的 Vite 输出到 `common/static/ui/`，
    静态资源由 Django staticfiles 在开发环境下以 /static/ 进行访问。
    """
    index_path = Path(__file__).resolve().parent / "static" / "ui" / "index.html"
    if not index_path.exists():
        raise Http404("UI not built. Run: cd ui && npm i && npm run build")
    return FileResponse(index_path.open("rb"), content_type="text/html; charset=utf-8")

