# -*- coding: utf-8 -*-
"""知乎收藏夹导出工具 - MCP Server"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

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

# 创建 MCP 服务器实例
app = Server("zhihu-collections")

# 全局状态
_cookies_loaded = False


def get_auth() -> CookieAuth:
    """获取 Cookie 授权实例"""
    auth = CookieAuth()
    auth.load_cookies()
    return auth


def get_fetcher():
    """获取抓取器实例"""
    auth = get_auth()
    return ZhihuFetcher(auth.get_cookies())


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    return [
        Tool(
            name="list_collections",
            description="列出用户所有知乎收藏夹",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="export_collection",
            description="导出指定知乎收藏夹为 Markdown、PDF、HTML 或 CSV 格式",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "收藏夹 ID，如 998150123"
                    },
                    "formats": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["md", "pdf", "html", "csv"]},
                        "description": "导出格式列表，默认为 ['md']"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "输出目录路径（可选，默认为 ./downloads）"
                    }
                },
                "required": ["collection_id"]
            }
        ),
        Tool(
            name="get_collection_info",
            description="获取指定收藏夹的基本信息（文章数量等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "收藏夹 ID"
                    }
                },
                "required": ["collection_id"]
            }
        ),
        Tool(
            name="search_collections",
            description="在收藏夹列表中搜索包含关键词的收藏夹",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["keyword"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    try:
        if name == "list_collections":
            return await list_collections_handler()
        elif name == "export_collection":
            return await export_collection_handler(arguments)
        elif name == "get_collection_info":
            return await get_collection_info_handler(arguments)
        elif name == "search_collections":
            return await search_collections_handler(arguments)
        else:
            return [TextContent(type="text", text=f"未知工具：{name}")]
    except Exception as e:
        logger.exception("工具调用失败")
        return [TextContent(type="text", text=f"错误：{str(e)}")]


async def list_collections_handler() -> list[TextContent]:
    """处理 list_collections 工具调用"""
    try:
        fetcher = get_fetcher()
        collections = fetcher.fetch_collection_list()

        if not collections:
            return [TextContent(
                type="text",
                text="⚠️ 暂时无法获取收藏夹列表\n\n"
                     "请使用 Web UI 方式访问：\n"
                     "1. 运行 `python3 web/server.py`\n"
                     "2. 访问 http://localhost:8000\n\n"
                     "或者手动输入收藏夹 ID 进行导出"
            )]

        result = f"📚 共找到 {len(collections)} 个收藏夹：\n\n"
        for i, coll in enumerate(collections, 1):
            name = coll.get("title", "未命名")
            creator = coll.get("creator", {}).get("name", "未知")
            count = coll.get("count", 0)
            result += f"{i}. **{name}**\n"
            result += f"   创建者：{creator}\n"
            result += f"   内容数：{count}\n"
            result += f"   ID: {coll.get('id', 'N/A')}\n\n"

        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.exception("获取收藏夹列表失败")
        return [TextContent(type="text", text=f"获取收藏夹列表失败：{str(e)}")]


async def export_collection_handler(args: dict) -> list[TextContent]:
    """处理 export_collection 工具调用"""
    collection_id = args.get("collection_id")
    formats = args.get("formats", ["md"])
    output_dir = args.get("output_dir", "./downloads")

    if not collection_id:
        return [TextContent(type="text", text="❌ 错误：需要提供 collection_id 参数")]

    # 检查 Cookie 授权
    auth = get_auth()
    if not auth.load_cookies() or not auth.validate_cookies():
        return [TextContent(type="text", text="❌ Cookie 未授权，请先运行 `auth` 命令配置 Cookie")]

    cookies = auth.get_cookies()
    fetcher = get_fetcher()

    # 获取收藏夹内容
    urls, titles = fetcher.get_collection_urls(collection_id)

    if not urls:
        return [TextContent(type="text", text=f"❌ 收藏夹为空或获取失败：{collection_id}")]

    result = f"🚀 开始导出收藏夹\n"
    result += f"🆔 收藏夹 ID: {collection_id}\n"
    result += f"📝 文章数量：{len(urls)}\n"
    result += f"📁 输出目录：{output_dir}\n"
    result += f"📄 导出格式：{', '.join(formats)}\n\n"

    # 创建输出目录
    collection_dir = os.path.join(output_dir, f"collection_{collection_id}")
    os.makedirs(collection_dir, exist_ok=True)

    headers = fetcher.headers
    metadata_list = []
    success_count = 0
    fail_count = 0

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
                metadata_list.append({
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                    "status": "failed"
                })
                fail_count += 1
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

            safe_title = safe_filename(title, max_length=50)

            # 导出 Markdown
            if "md" in formats:
                md_output_dir = os.path.join(collection_dir, "markdown")
                os.makedirs(md_output_dir, exist_ok=True)
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
                pdf_output_dir = os.path.join(collection_dir, "pdf")
                os.makedirs(pdf_output_dir, exist_ok=True)
                pdf_file = os.path.join(pdf_output_dir, f"{safe_title}.pdf")
                html_to_pdf(html_content, pdf_file, title=title)

            # 导出 HTML
            if "html" in formats:
                html_output_dir = os.path.join(collection_dir, "html")
                os.makedirs(html_output_dir, exist_ok=True)
                html_file = os.path.join(html_output_dir, f"{safe_title}.html")
                html_to_single_file(
                    html_content, html_file, title=title,
                    original_url=url, headers=headers, cookies=cookies
                )

            success_count += 1

        except Exception as e:
            logger.error(f"导出失败：{title}, 错误：{str(e)}")
            fail_count += 1

    # 导出 CSV
    if "csv" in formats:
        csv_output_dir = os.path.join(collection_dir, "csv")
        os.makedirs(csv_output_dir, exist_ok=True)
        csv_file = os.path.join(csv_output_dir, f"collection_{collection_id}_metadata.csv")
        export_to_csv(metadata_list, csv_file, collection_name=f"收藏夹_{collection_id}")

    result += f"\n✅ 导出完成！\n"
    result += f"   成功：{success_count} 篇\n"
    result += f"   失败：{fail_count} 篇\n"
    result += f"   保存路径：{collection_dir}"

    return [TextContent(type="text", text=result)]


async def get_collection_info_handler(args: dict) -> list[TextContent]:
    """处理 get_collection_info 工具调用"""
    collection_id = args.get("collection_id")

    if not collection_id:
        return [TextContent(type="text", text="❌ 错误：需要提供 collection_id 参数")]

    try:
        fetcher = get_fetcher()
        urls, titles = fetcher.get_collection_urls(collection_id)

        if not urls:
            return [TextContent(type="text", text=f"❌ 收藏夹为空或获取失败：{collection_id}")]

        result = f"📊 收藏夹信息\n\n"
        result += f"🆔 收藏夹 ID: {collection_id}\n"
        result += f"📝 文章数量：{len(urls)}\n\n"

        if titles:
            result += f"📄 文章标题（前 5 个）：\n"
            for i, title in enumerate(titles[:5], 1):
                result += f"  {i}. {title}\n"
            if len(titles) > 5:
                result += f"  ... 还有 {len(titles) - 5} 篇"

        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.exception("获取收藏夹信息失败")
        return [TextContent(type="text", text=f"获取收藏夹信息失败：{str(e)}")]


async def search_collections_handler(args: dict) -> list[TextContent]:
    """处理 search_collections 工具调用"""
    keyword = args.get("keyword", "")

    if not keyword:
        return [TextContent(type="text", text="❌ 错误：需要提供 keyword 参数")]

    try:
        fetcher = get_fetcher()
        collections = fetcher.fetch_collection_list()

        if not collections:
            return [TextContent(type="text", text="❌ 无法获取收藏夹列表")]

        # 搜索匹配的收藏夹
        matched = []
        for coll in collections:
            name = coll.get("title", "")
            if keyword.lower() in name.lower():
                matched.append(coll)

        if not matched:
            return [TextContent(type="text", text=f"🔍 没有找到包含 '{keyword}' 的收藏夹")]

        result = f"🔍 搜索结果（关键词：{keyword}）：\n\n"
        for i, coll in enumerate(matched, 1):
            name = coll.get("title", "未命名")
            creator = coll.get("creator", {}).get("name", "未知")
            count = coll.get("count", 0)
            result += f"{i}. **{name}**\n"
            result += f"   创建者：{creator}\n"
            result += f"   内容数：{count}\n"
            result += f"   ID: {coll.get('id', 'N/A')}\n\n"

        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.exception("搜索收藏夹失败")
        return [TextContent(type="text", text=f"搜索失败：{str(e)}")]


async def main():
    """MCP 服务器主入口"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
