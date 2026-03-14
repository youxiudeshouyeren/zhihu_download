# -*- coding: utf-8 -*-
"""Web UI 服务器 - FastAPI 后端"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.auth.cookie_auth import CookieAuth
from src.crawler.fetcher import ZhihuFetcher
from src.converter.markdown import html_to_markdown
from src.converter.pdf import html_to_pdf
from src.converter.html import html_to_single_file
from src.converter.csv import export_to_csv
from src.utils.helpers import safe_filename

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局状态
export_tasks: Dict[str, Dict[str, Any]] = {}
app_data = {
    "cookies_loaded": False,
    "collections": [],
    "output_dir": "./downloads"
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时加载 Cookie
    auth = CookieAuth()
    if auth.load_cookies() and auth.validate_cookies():
        app_data["cookies_loaded"] = True
        logger.info("Cookie 已加载")
    yield
    # 关闭时清理
    logger.info("Web 服务已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="知乎收藏夹导出工具",
    description="支持 Markdown、PDF、HTML、CSV 格式导出",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# ==================== 工具函数 ====================

def get_auth() -> CookieAuth:
    """获取 Cookie 授权实例"""
    auth = CookieAuth()
    auth.load_cookies()
    return auth


def get_fetcher():
    """获取抓取器实例"""
    auth = get_auth()
    return ZhihuFetcher(auth.get_cookies())


# ==================== API 接口 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Template not found</h1>")


@app.get("/api/status")
async def get_status():
    """获取应用状态"""
    return {
        "cookies_loaded": app_data["cookies_loaded"],
        "collections_count": len(app_data["collections"])
    }


@app.get("/api/collections")
async def list_collections():
    """获取收藏夹列表"""
    if not app_data["cookies_loaded"]:
        raise HTTPException(status_code=401, detail="请先授权 Cookie")

    try:
        fetcher = get_fetcher()
        collections = fetcher.fetch_collection_list()
        app_data["collections"] = collections
        return {"collections": collections}
    except Exception as e:
        logger.error(f"获取收藏夹失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/collections/{collection_id}/info")
async def get_collection_info(collection_id: str):
    """获取单个收藏夹信息"""
    if not app_data["cookies_loaded"]:
        raise HTTPException(status_code=401, detail="请先授权 Cookie")

    try:
        fetcher = get_fetcher()
        # 获取收藏夹内容来判断是否有效
        urls, titles = fetcher.get_collection_urls(collection_id)

        if not urls and not titles:
            # 尝试获取总数来判断
            count = fetcher.get_collection_item_count(collection_id)
            if count is not None:
                return {"id": collection_id, "title": f"收藏夹 {collection_id}", "count": count}
            raise HTTPException(status_code=404, detail="收藏夹不存在或无法访问")

        return {"id": collection_id, "title": titles[0] if titles else f"收藏夹 {collection_id}", "count": len(urls)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收藏夹信息失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def create_export_task(request: dict, background_tasks: BackgroundTasks = None):
    """创建导出任务"""
    if not app_data["cookies_loaded"]:
        raise HTTPException(status_code=401, detail="请先授权 Cookie")

    collection_id = request.get("collection_id")
    formats = request.get("formats", ["md"])
    articles = request.get("articles", [])

    if not collection_id:
        raise HTTPException(status_code=400, detail="缺少 collection_id")

    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 创建任务记录
    export_tasks[task_id] = {
        "id": task_id,
        "collection_id": collection_id,
        "formats": formats,
        "status": "pending",
        "progress": 0,
        "total": 0,
        "success": 0,
        "failed": 0,
        "created_at": datetime.now().isoformat(),
        "error": None,
        "articles": articles  # 保存选中的文章
    }

    # 在后台执行导出任务
    if background_tasks:
        background_tasks.add_task(run_export_task, task_id)

    return {"task_id": task_id, "status": "pending"}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return export_tasks[task_id]


@app.get("/api/tasks")
async def list_tasks():
    """获取所有任务列表"""
    return {"tasks": list(export_tasks.values())}


@app.post("/api/cookies/check")
async def check_cookies():
    """检查 Cookie 状态"""
    auth = get_auth()
    if auth.load_cookies() and auth.validate_cookies():
        app_data["cookies_loaded"] = True
        return {"status": "valid", "user_id": auth.get_user_id()}
    else:
        app_data["cookies_loaded"] = False
        raise HTTPException(status_code=401, detail="Cookie 无效或已过期")


@app.post("/api/cookies")
async def save_cookies(cookies: dict):
    """保存 Cookie"""
    try:
        auth = CookieAuth()
        cookie_dict = cookies.get("cookies", {})

        # 验证 Cookie
        temp_auth = CookieAuth()
        temp_auth._cookies = cookie_dict
        if not temp_auth.validate_cookies():
            raise HTTPException(status_code=400, detail="Cookie 验证失败")

        # 保存 Cookie
        if auth.save_cookies(cookie_dict, temp_auth.get_user_id()):
            app_data["cookies_loaded"] = True
            return {"status": "success", "user_id": temp_auth.get_user_id()}
        else:
            raise HTTPException(status_code=500, detail="Cookie 保存失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存 Cookie 失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cookies")
async def get_cookies():
    """获取当前 Cookie"""
    auth = get_auth()
    if auth.load_cookies():
        return {"cookies": auth.get_cookies(), "status": "loaded"}
    else:
        return {"cookies": {}, "status": "not_found"}


@app.delete("/api/cookies")
async def delete_cookies():
    """清除 Cookie"""
    auth = CookieAuth()
    auth.clear_cookies()
    app_data["cookies_loaded"] = False
    return {"status": "success"}


@app.get("/api/collections/{collection_id}/articles")
async def get_collection_articles(collection_id: str):
    """获取收藏夹文章列表"""
    if not app_data["cookies_loaded"]:
        raise HTTPException(status_code=401, detail="请先授权 Cookie")

    try:
        fetcher = get_fetcher()
        urls, titles = fetcher.get_collection_urls(collection_id)

        articles = []
        for url, title in zip(urls, titles):
            articles.append({
                "url": url,
                "title": title,
                "type": "article" if "zhuanlan" in url else "answer"
            })

        return {"articles": articles}
    except Exception as e:
        logger.error(f"获取文章列表失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/filesystem/list")
async def list_directory(path: str = None):
    """列出目录内容"""
    try:
        # 如果 path 为空，返回根目录和常用目录
        if not path:
            # 获取用户主目录
            home_dir = str(Path.home())
            cwd = os.getcwd()

            return {
                "path": "/",
                "parent": None,
                "folders": [
                    {"name": "主目录", "path": home_dir, "type": "home"},
                    {"name": "当前目录", "path": cwd, "type": "cwd"},
                    {"name": "下载目录", "path": str(Path.home() / "Downloads"), "type": "folder"},
                    {"name": "桌面", "path": str(Path.home() / "Desktop"), "type": "folder"},
                    {"name": "文档", "path": str(Path.home() / "Documents"), "type": "folder"},
                ]
            }

        # 验证路径安全性 - 防止目录遍历攻击
        base_path = Path(os.path.abspath(os.path.sep))
        target_path = Path(os.path.abspath(path))

        # 确保目标路径是 base_path 的子目录
        try:
            target_path.relative_to(base_path)
        except ValueError:
            # 如果是 Windows 路径（包含盘符），特殊处理
            if len(path) == 2 and path[1] == ':':
                pass  # 允许访问盘符根目录
            else:
                raise HTTPException(status_code=403, detail="无权访问该路径")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="路径不存在")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="不是目录")

        items = []
        try:
            for item in target_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "folder"
                    })
        except PermissionError:
            pass  # 忽略无权限的目录

        # 按名称排序
        items.sort(key=lambda x: x["name"].lower())

        # 获取父目录
        parent = str(target_path.parent) if target_path != base_path else None

        return {
            "path": str(target_path),
            "parent": parent,
            "folders": items
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出目录失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filesystem/validate")
async def validate_path(request: dict):
    """验证路径是否存在且可写"""
    try:
        path = request.get("path")
        if not path:
            return {"valid": False, "error": "路径为空"}

        target = Path(path)

        # 如果目录不存在，尝试创建
        if not target.exists():
            try:
                target.mkdir(parents=True, exist_ok=True)
                return {"valid": True, "message": f"目录已创建：{path}"}
            except Exception as e:
                return {"valid": False, "error": f"无法创建目录：{str(e)}"}

        # 检查是否是目录
        if not target.is_dir():
            return {"valid": False, "error": "路径存在但不是目录"}

        # 检查是否可写
        try:
            test_file = target / ".zhihu_export_test"
            test_file.touch()
            test_file.unlink()
            return {"valid": True, "message": "路径可用"}
        except PermissionError:
            return {"valid": False, "error": "目录不可写"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    except Exception as e:
        logger.error(f"验证路径失败：{str(e)}")
        return {"valid": False, "error": str(e)}


# ==================== 导出任务执行 ====================

def run_export_task(task_id: str):
    """执行导出任务"""
    try:
        task = export_tasks[task_id]
        task["status"] = "running"

        collection_id = task["collection_id"]
        formats = task["formats"]
        selected_articles = task.get("articles", [])  # 选中的文章列表

        # 获取授权
        auth = get_auth()
        cookies = auth.get_cookies()
        fetcher = ZhihuFetcher(cookies)

        # 创建输出目录
        output_dir = os.path.join(app_data["output_dir"], f"collection_{collection_id}")
        os.makedirs(output_dir, exist_ok=True)

        # 获取收藏夹内容
        urls, titles = fetcher.get_collection_urls(collection_id)

        if not urls:
            task["status"] = "failed"
            task["error"] = "收藏夹为空或获取失败"
            return

        # 如果有选中的文章，只导出选中的
        if selected_articles:
            # 过滤出选中的文章
            selected_urls = [article["url"] for article in selected_articles]
            filtered_items = [(url, title) for url, title in zip(urls, titles) if url in selected_urls]
            urls, titles = zip(*filtered_items) if filtered_items else ([], [])
            urls, titles = list(urls), list(titles)

        task["total"] = len(urls)
        headers = fetcher.headers
        metadata_list = []

        # 处理每篇文章
        for i, (url, title) in enumerate(zip(urls, titles)):
            try:
                # 获取内容
                if "zhuanlan" in url:
                    html_content = fetcher.get_single_post_content(url)
                    content_type = "article"
                else:
                    html_content = fetcher.get_single_answer_content(url)
                    content_type = "answer"

                if not html_content:
                    task["failed"] += 1
                    metadata_list.append({
                        "title": title,
                        "url": url,
                        "content_type": content_type,
                        "status": "failed"
                    })
                    continue

                # 收集元数据
                metadata_list.append({
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                    "status": "success"
                })

                # 添加版权声明
                copyright_notice = f"""
                <div class="copyright-notice">
                    <p>本内容仅供个人非商用学习备份使用，版权归知乎平台及原作者所有。</p>
                    <p>原文链接：<a href="{url}">{url}</a></p>
                </div>
                """
                html_content += copyright_notice

                # 导出 Markdown
                if "md" in formats:
                    md_output_dir = os.path.join(output_dir, "markdown")
                    os.makedirs(md_output_dir, exist_ok=True)
                    safe_title = safe_filename(title, max_length=50)
                    md_file = os.path.join(md_output_dir, f"{safe_title}.md")

                    md_content = html_to_markdown(
                        html_content, download_dir=md_output_dir, headers=headers,
                        cookies=cookies, article_title=safe_title
                    )
                    md_content = f"> {url}\n\n" + md_content

                    with open(md_file, "w", encoding="utf-8") as f:
                        f.write(md_content)

                # 导出 PDF
                if "pdf" in formats:
                    pdf_output_dir = os.path.join(output_dir, "pdf")
                    os.makedirs(pdf_output_dir, exist_ok=True)
                    safe_title = safe_filename(title, max_length=50)
                    pdf_file = os.path.join(pdf_output_dir, f"{safe_title}.pdf")
                    html_to_pdf(html_content, pdf_file, title=title)

                # 导出 HTML
                if "html" in formats:
                    html_output_dir = os.path.join(output_dir, "html")
                    os.makedirs(html_output_dir, exist_ok=True)
                    safe_title = safe_filename(title, max_length=50)
                    html_file = os.path.join(html_output_dir, f"{safe_title}.html")
                    html_to_single_file(
                        html_content, html_file, title=title,
                        original_url=url, headers=headers, cookies=cookies
                    )

                task["success"] += 1

            except Exception as e:
                logger.error(f"导出失败：{title}, 错误：{str(e)}")
                task["failed"] += 1

            # 更新进度
            task["progress"] = i + 1

        # 导出 CSV
        if "csv" in formats:
            csv_output_dir = os.path.join(output_dir, "csv")
            os.makedirs(csv_output_dir, exist_ok=True)
            csv_file = os.path.join(csv_output_dir, f"collection_{collection_id}_metadata.csv")
            export_to_csv(metadata_list, csv_file, collection_name=f"收藏夹_{collection_id}")

        task["status"] = "completed"

    except Exception as e:
        logger.error(f"任务执行失败：{task_id}, 错误：{str(e)}")
        if task_id in export_tasks:
            export_tasks[task_id]["status"] = "failed"
            export_tasks[task_id]["error"] = str(e)


# ==================== 主入口 ====================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
