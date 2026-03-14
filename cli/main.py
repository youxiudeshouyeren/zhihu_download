# -*- coding: utf-8 -*-
"""知乎收藏夹导出工具 - 命令行入口"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm

# 导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.auth.cookie_auth import CookieAuth
from src.crawler.fetcher import ZhihuFetcher
from src.converter.markdown import html_to_markdown
from src.converter.pdf import html_to_pdf
from src.converter.html import html_to_single_file
from src.converter.csv import export_to_csv
from src.utils.helpers import safe_filename

# 初始化 rich console
console = Console()

# 创建 CLI 应用
app = typer.Typer(
    name="zhihu-download",
    help="知乎收藏夹导出工具 - 支持 Markdown、PDF、HTML、CSV 格式导出",
    add_completion=False,
)


# ==================== 全局状态 ====================

# 全局日志配置
log_dir = None


def setup_logging(output_dir: str):
    """配置日志"""
    global log_dir
    log_dir = os.path.join(output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir, f"zhihu_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


# ==================== 授权命令 ====================


@app.command("auth")
def auth_command(
    cookie_string: Optional[str] = typer.Argument(
        None, help="Cookie 字符串（可选，如不提供则提示输入）"
    ),
    json_path: Optional[str] = typer.Option(
        None, "--json", "-j", help="从 JSON 文件加载 Cookie"
    ),
):
    """配置知乎 Cookie 授权"""
    console.print("[bold blue]知乎收藏夹导出工具 - Cookie 授权[/bold blue]\n")

    auth = CookieAuth()

    # 检查是否已有保存的 Cookie
    if auth.load_cookies():
        console.print("[green]✓ 已找到保存的 Cookie[/green]")
        if auth.validate_cookies():
            console.print(f"[green]✓ Cookie 验证成功，用户 ID: {auth.get_user_id()}[/green]")
            if Confirm.ask("是否重新配置 Cookie？", default=False):
                pass  # 继续重新配置
            else:
                console.print("[blue]使用现有 Cookie[/blue]")
                return

    # 清除旧 Cookie
    auth.clear_cookies()

    # 获取 Cookie
    cookies = None

    if json_path:
        console.print(f"[blue]从 JSON 文件加载 Cookie: {json_path}[/blue]")
        cookies = CookieAuth.load_from_json(json_path)
        if not cookies:
            console.print("[red]✗ JSON 文件加载失败[/red]")
            raise typer.Exit(1)

    elif cookie_string:
        console.print("[blue]使用命令行提供的 Cookie[/blue]")
        cookies = CookieAuth.parse_cookie_string(cookie_string)

    else:
        # 交互式输入
        console.print(
            "[yellow]请输入知乎 Cookie 字符串[/yellow]\n"
            "获取方式：在浏览器中打开知乎 -> F12 开发者工具 -> Network 标签 -> 刷新页面 -> 复制请求头中的 Cookie\n"
            "或直接粘贴 cookies.json 文件内容\n"
        )
        cookie_string = Prompt.ask("Cookie")
        cookies = CookieAuth.parse_cookie_string(cookie_string)

    # 验证 Cookie
    console.print("[blue]正在验证 Cookie...[/blue]")
    temp_auth = CookieAuth()
    temp_auth._cookies = cookies
    if not temp_auth.validate_cookies():
        console.print("[red]✗ Cookie 验证失败，请检查是否正确[/red]")
        raise typer.Exit(1)

    # 保存 Cookie
    if auth.save_cookies(cookies, temp_auth.get_user_id()):
        console.print("[green]✓ Cookie 保存成功！[/green]")
        console.print(f"[green]✓ 用户 ID: {temp_auth.get_user_id()}[/green]")
    else:
        console.print("[red]✗ Cookie 保存失败[/red]")
        raise typer.Exit(1)


# ==================== 收藏夹命令 ====================


@app.command("list")
def list_collections():
    """列出所有收藏夹"""
    console.print("[bold blue]获取收藏夹列表...[/bold blue]\n")

    # 加载 Cookie
    auth = CookieAuth()
    if not auth.load_cookies():
        console.print("[red]✗ 未找到 Cookie，请先运行 `zhihu-download auth` 授权[/red]")
        raise typer.Exit(1)

    if not auth.validate_cookies():
        console.print("[red]✗ Cookie 已过期，请重新运行 `zhihu-download auth` 授权[/red]")
        raise typer.Exit(1)

    # 获取收藏夹
    fetcher = ZhihuFetcher(auth.get_cookies())
    collections = fetcher.fetch_collection_list()

    if not collections:
        console.print("[yellow]⚠️  暂时无法通过 API 获取收藏夹列表[/yellow]")
        console.print("\n[bold]替代方案：[/bold]")
        console.print("1. [blue]使用 Web UI（推荐）[/blue]: 运行 `python3 web/server.py`，然后访问 http://localhost:8000")
        console.print("2. [blue]手动输入收藏夹 ID[/blue]: 从知乎收藏夹 URL 中提取 ID")
        console.print("   例如：https://www.zhihu.com/collection/998150123 的 ID 是 998150123")
        console.print("\n[bold]导出命令示例：[/bold]")
        console.print("  zhihu-download export 998150123 -f md -f pdf")
        raise typer.Exit(0)

    # 显示表格
    table = Table(title=f"共找到 {len(collections)} 个收藏夹")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("创建者", style="yellow")
    table.add_column("内容数", justify="right", style="magenta")

    for coll in collections:
        table.add_row(
            str(coll.get("id", "N/A")),
            coll.get("title", "未命名"),
            coll.get("creator", {}).get("name", "未知"),
            str(coll.get("count", 0)),
        )

    console.print(table)


# ==================== 导出命令 ====================


@app.command("zip")
def zip_collection(
    collection_id: str = typer.Argument(..., help="收藏夹 ID"),
    output_dir: str = typer.Option(
        "./downloads", "--output", "-o", help="输出目录"
    ),
    formats: List[str] = typer.Option(
        None, "--format", "-f", help="包含的格式（可多次指定，如 -f md -f pdf）"
    ),
    no_timestamp: bool = typer.Option(
        False, "--no-timestamp", help="文件名不包含时间戳"
    ),
):
    """将已导出的收藏夹打包为 ZIP"""
    console.print(f"[bold blue]打包收藏夹：{collection_id}[/bold blue]\n")

    collection_dir = os.path.join(output_dir, f"collection_{collection_id}")

    if not os.path.exists(collection_dir):
        console.print(f"[red]✗ 收藏夹目录不存在：{collection_dir}[/red]")
        console.print("[blue]请先使用 `export` 命令导出收藏夹[/blue]")
        raise typer.Exit(1)

    from src.exporter.zipper import create_collection_zip

    try:
        zip_path = create_collection_zip(
            collection_id=collection_id,
            output_dir=output_dir,
            formats=formats,
            include_metadata=True,
            include_timestamp=not no_timestamp
        )

        console.print(f"\n[bold green]✓ 打包完成！[/bold green]")
        console.print(f"[blue]ZIP 文件：{zip_path}[/blue]")

        # 显示文件信息
        from src.exporter.zipper import get_zip_info, format_size
        info = get_zip_info(zip_path)
        console.print(f"\n[dim]文件信息：[/dim]")
        console.print(f"  文件数：{info['total_files']}")
        console.print(f"  压缩后大小：{format_size(info['compressed_size'])}")
        console.print(f"  压缩率：{info['compression_ratio']:.1f}%")

    except Exception as e:
        console.print(f"[red]✗ 打包失败：{str(e)}[/red]")
        raise typer.Exit(1)


@app.command("export")
def export_collection(
    collection_id: str = typer.Argument(..., help="收藏夹 ID"),
    output_dir: str = typer.Option(
        "./downloads", "--output", "-o", help="输出目录"
    ),
    format: List[str] = typer.Option(
        ["md"], "--format", "-f", help="导出格式：md, pdf, html, csv"
    ),
    delay_min: int = typer.Option(1, "--delay-min", help="最小延迟（秒）"),
    delay_max: int = typer.Option(3, "--delay-max", help="最大延迟（秒）"),
    resume: bool = typer.Option(
        False, "--resume", "-r", help="断点续传，跳过已导出的文章"
    ),
    force: bool = typer.Option(
        False, "--force", help="强制重新导出所有内容，忽略已存在的文件"
    ),
    dedupe: bool = typer.Option(
        False, "--dedupe", help="启用内容去重，跳过内容相同的文章"
    ),
):
    """导出指定收藏夹"""
    console.print(f"[bold blue]开始导出收藏夹：{collection_id}[/bold blue]\n")

    # 配置日志
    setup_logging(output_dir)
    logger = logging.getLogger(__name__)
    logger.info(f"开始导出收藏夹：{collection_id}")

    # 加载 Cookie
    auth = CookieAuth()
    if not auth.load_cookies():
        console.print("[red]✗ 未找到 Cookie，请先运行 `zhihu-download auth` 授权[/red]")
        raise typer.Exit(1)

    if not auth.validate_cookies():
        console.print("[red]✗ Cookie 已过期，请重新运行 `zhihu-download auth` 授权[/red]")
        raise typer.Exit(1)

    cookies = auth.get_cookies()

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    collection_dir = os.path.join(output_dir, f"collection_{collection_id}")
    os.makedirs(collection_dir, exist_ok=True)

    # 初始化进度追踪器（增量导出/断点续传）
    from src.exporter.progress import ExportProgress, ContentDeduplicator
    progress_tracker = ExportProgress(collection_id, output_dir)

    # 初始化内容去重器
    deduplicator = ContentDeduplicator(output_dir) if dedupe else None

    # 检查是否有之前的进度
    if resume and progress_tracker.should_resume():
        stats = progress_tracker.get_stats()
        console.print(f"[yellow]⚠️  发现未完成的导出任务[/yellow]")
        console.print(f"   总数：{stats['total']}, 已导出：{stats['exported']}, 失败：{stats['failed']}")
        if Confirm.ask("是否继续导出？"):
            pass  # 继续
        else:
            progress_tracker.clear()
            console.print("[blue]已清除进度记录，重新开始导出[/blue]")

    # 强制重新导出
    if force:
        progress_tracker.clear()
        console.print("[blue]强制重新导出模式[/blue]")

    # 初始化抓取器
    fetcher = ZhihuFetcher(
        cookies, request_delay_range=(delay_min * 1000, delay_max * 1000)
    )

    # 获取收藏夹内容
    console.print("[blue]正在获取收藏夹内容列表...[/blue]")
    urls, titles = fetcher.get_collection_urls(collection_id)

    if not urls:
        console.print("[red]✗ 收藏夹为空或获取失败[/red]")
        raise typer.Exit(1)

    console.print(f"[green]✓ 找到 {len(urls)} 篇内容[/green]\n")

    # 准备转换配置
    headers = fetcher.headers

    # 存储元数据用于 CSV 导出
    metadata_list = []

    # 导出进度
    success_count = 0
    fail_count = 0
    skipped_count = 0
    duplicate_count = 0

    # 初始化进度追踪器
    progress_tracker.start(len(urls))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]导出中...", total=len(urls))

        for i, (url, title) in enumerate(zip(urls, titles)):
            # 检查是否已导出（增量导出）
            if progress_tracker.is_exported(url):
                console.print(f"[dim]⏭  跳过已导出：{title[:30]}...[/dim]")
                skipped_count += 1
                progress.advance(task)
                continue

            progress.update(task, description=f"[cyan]处理：{title[:30]}...")

            try:
                # 获取内容
                if "zhuanlan" in url:
                    html_content = fetcher.get_single_post_content(url)
                    content_type = "article"
                else:
                    html_content = fetcher.get_single_answer_content(url)
                    content_type = "answer"

                if not html_content:
                    console.print(f"[yellow]⚠ 获取失败：{title}[/yellow]")
                    progress_tracker.mark_failed(url, title, "获取内容失败")
                    fail_count += 1
                    progress.advance(task)
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
                if "md" in format:
                    md_output_dir = os.path.join(collection_dir, "markdown")
                    os.makedirs(md_output_dir, exist_ok=True)

                    # 生成安全的文件名
                    safe_title = safe_filename(title, max_length=50)
                    md_file = os.path.join(md_output_dir, f"{safe_title}.md")

                    # 转换 Markdown（传递文章标题用于创建专属图片目录）
                    md_content = html_to_markdown(
                        html_content, download_dir=md_output_dir, headers=headers,
                        cookies=cookies, article_title=safe_title
                    )
                    # 添加 URL 引用
                    md_content = f"> {url}\n\n" + md_content

                    with open(md_file, "w", encoding="utf-8") as f:
                        f.write(md_content)

                # 导出 PDF
                if "pdf" in format:
                    pdf_output_dir = os.path.join(collection_dir, "pdf")
                    os.makedirs(pdf_output_dir, exist_ok=True)

                    # 生成安全的文件名
                    safe_title = safe_filename(title, max_length=50)
                    pdf_file = os.path.join(pdf_output_dir, f"{safe_title}.pdf")

                    html_to_pdf(html_content, pdf_file, title=title)

                # 导出 HTML 单文件
                if "html" in format:
                    html_output_dir = os.path.join(collection_dir, "html")
                    os.makedirs(html_output_dir, exist_ok=True)

                    # 生成安全的文件名
                    safe_title = safe_filename(title, max_length=50)
                    html_file = os.path.join(html_output_dir, f"{safe_title}.html")

                    html_to_single_file(
                        html_content, html_file, title=title,
                        original_url=url, headers=headers, cookies=cookies
                    )

                # 标记为已导出
                progress_tracker.mark_exported(url, title)
                success_count += 1

            except Exception as e:
                logger.error(f"导出失败：{title}, 错误：{str(e)}")
                console.print(f"[red]✗ 导出失败：{title} - {str(e)}[/red]")
                progress_tracker.mark_failed(url, title, str(e))
                fail_count += 1
                # 记录失败的元数据
                metadata_list.append({
                    "title": title,
                    "url": url,
                    "content_type": "unknown",
                    "status": "failed",
                    "error": str(e)
                })

            progress.advance(task)

    # 导出 CSV
    if "csv" in format:
        csv_output_dir = os.path.join(collection_dir, "csv")
        os.makedirs(csv_output_dir, exist_ok=True)

        csv_file = os.path.join(csv_output_dir, f"collection_{collection_id}_metadata.csv")
        console.print(f"\n[blue]正在导出元数据到 CSV: {csv_file}[/blue]")

        export_to_csv(metadata_list, csv_file, collection_name=f"收藏夹_{collection_id}")

    # 标记导出完成
    progress_tracker.complete()

    # 总结
    console.print("\n[bold green]✓ 导出完成！[/bold green]")
    console.print(f"[green]成功：{success_count} 篇[/green]")
    console.print(f"[yellow]失败：{fail_count} 篇[/yellow]")
    if skipped_count > 0:
        console.print(f"[dim]跳过：{skipped_count} 篇（已导出）[/dim]")
    console.print(f"[blue]保存路径：{collection_dir}[/blue]")


# ==================== 主入口 ====================


def main():
    """主入口"""
    app()


if __name__ == "__main__":
    main()
