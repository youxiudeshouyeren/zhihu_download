# -*- coding: utf-8 -*-
"""HTML 单文件格式转换模块 - 离线网页导出"""

import logging
import os
import base64
import re
from typing import Optional
import requests

logger = logging.getLogger(__name__)


# HTML 单文件模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {css_styles}
    </style>
</head>
<body>
    <article>
        <header>
            <h1>{title}</h1>
            <div class="meta">
                <span class="author">作者：{author}</span>
                <a href="{original_url}" class="source-link" target="_blank">查看原文</a>
            </div>
        </header>
        <div class="content">
            {content}
        </div>
        <footer class="copyright-notice">
            <p>本内容仅供个人非商用学习备份使用，版权归知乎平台及原作者所有。</p>
            <p>原文链接：<a href="{original_url}">{original_url}</a></p>
        </footer>
    </article>
</body>
</html>
"""

# CSS 样式
CSS_STYLES = """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    line-height: 1.8;
    color: #333;
    background-color: #f5f5f5;
    padding: 20px;
}

article {
    max-width: 800px;
    margin: 0 auto;
    background: #fff;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

header {
    border-bottom: 2px solid #eee;
    padding-bottom: 20px;
    margin-bottom: 30px;
}

h1 {
    font-size: 28px;
    line-height: 1.4;
    margin-bottom: 15px;
    color: #1a1a1a;
}

.meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
    color: #666;
}

.author {
    color: #0066ff;
}

.source-link {
    color: #0066ff;
    text-decoration: none;
}

.source-link:hover {
    text-decoration: underline;
}

.content {
    font-size: 16px;
}

.content h1, .content h2, .content h3, .content h4, .content h5, .content h6 {
    margin-top: 30px;
    margin-bottom: 15px;
    color: #1a1a1a;
}

.content p {
    margin-bottom: 15px;
    text-align: justify;
}

.content img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 15px auto;
}

.content pre {
    background: #f6f8fa;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin-bottom: 15px;
}

.content code {
    background: #f6f8fa;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "Noto Sans Mono CJK SC", "Consolas", monospace;
    font-size: 14px;
}

.content blockquote {
    border-left: 4px solid #0066ff;
    padding-left: 15px;
    margin: 15px 0;
    color: #666;
    background: #f9f9f9;
    padding: 10px 15px;
}

.content table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 15px;
}

.content th, .content td {
    border: 1px solid #e0e0e0;
    padding: 10px;
    text-align: left;
}

.content th {
    background: #f5f5f5;
    font-weight: bold;
}

.content ul, .content ol {
    padding-left: 30px;
    margin-bottom: 15px;
}

.content li {
    margin-bottom: 8px;
}

.content a {
    color: #0066ff;
    text-decoration: none;
}

.content a:hover {
    text-decoration: underline;
}

.copyright-notice {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #eee;
    font-size: 12px;
    color: #999;
    text-align: center;
}
"""


class HTMLConverter:
    """HTML 单文件转换器"""

    def __init__(self, headers: dict = None, cookies: dict = None):
        """
        初始化转换器

        Args:
            headers: 请求头
            cookies: Cookie
        """
        self.headers = headers or {}
        self.cookies = cookies or {}

    def convert(
        self,
        html_content: str,
        output_path: str,
        title: str = "",
        author: str = "",
        original_url: str = "",
        embed_images: bool = True
    ) -> bool:
        """
        将 HTML 转换为单文件网页

        Args:
            html_content: HTML 内容
            output_path: 输出文件路径
            title: 文档标题
            author: 作者
            original_url: 原文链接
            embed_images: 是否嵌入图片为 Base64

        Returns:
            是否转换成功
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 处理图片（转换为 Base64）
            if embed_images:
                html_content = self._embed_images(html_content)

            # 生成完整 HTML
            full_html = HTML_TEMPLATE.format(
                title=title or "知乎文章",
                author=author or "未知作者",
                original_url=original_url or "#",
                css_styles=CSS_STYLES,
                content=html_content
            )

            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_html)

            logger.info(f"HTML 单文件生成成功：{output_path}")
            return True

        except Exception as e:
            logger.error(f"HTML 转换失败：{str(e)}")
            return False

    def _embed_images(self, html_content: str) -> str:
        """
        将 HTML 中的图片转换为 Base64 嵌入

        Args:
            html_content: HTML 内容

        Returns:
            嵌入图片后的 HTML
        """
        def replace_img(match):
            img_tag = match.group(0)
            src_match = re.search(r'src="([^"]+)"', img_tag)

            if not src_match:
                return img_tag

            src = src_match.group(1)

            # 跳过 SVG 占位图
            if "data:image/svg+xml" in src:
                return '<!-- image removed -->'

            # 已经是 Base64 的图片
            if src.startswith("data:"):
                return img_tag

            try:
                # 下载图片
                response = requests.get(src, headers=self.headers, cookies=self.cookies, timeout=10)
                response.raise_for_status()

                # 判断图片类型
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                if 'png' in content_type:
                    content_type = 'image/png'
                elif 'gif' in content_type:
                    content_type = 'image/gif'
                else:
                    content_type = 'image/jpeg'

                # 转换为 Base64
                base64_data = base64.b64encode(response.content).decode('utf-8')
                data_uri = f"data:{content_type};base64,{base64_data}"

                # 替换 src
                return img_tag.replace(src, data_uri)

            except Exception as e:
                logger.warning(f"图片嵌入失败：{src}, 错误：{str(e)}")
                return img_tag

        # 替换所有 img 标签
        return re.sub(r'<img[^>]+>', replace_img, html_content)


def html_to_single_file(
    html_content: str,
    output_path: str,
    title: str = "",
    author: str = "",
    original_url: str = "",
    headers: dict = None,
    cookies: dict = None
) -> bool:
    """
    便捷函数：HTML 转单文件网页

    Args:
        html_content: HTML 内容
        output_path: 输出文件路径
        title: 文档标题
        author: 作者
        original_url: 原文链接
        headers: 请求头
        cookies: Cookie

    Returns:
        是否转换成功
    """
    converter = HTMLConverter(headers=headers, cookies=cookies)
    return converter.convert(html_content, output_path, title, author, original_url)
