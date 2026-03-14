# -*- coding: utf-8 -*-
"""PDF 转换模块 - 使用 weasyprint"""

import logging
import os
from typing import Optional
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)

# 使用 Noto Sans CJK SC 字体的中文 PDF 样式配置
CHINESE_CSS = """
@page {
    size: A4;
    margin: 2cm;

    @bottom-right {
        content: counter(page) " / " counter(pages);
        font-size: 10pt;
    }

    @top-center {
        content: string(title);
        font-size: 10pt;
        color: #666;
    }
}

html {
    font-family: "Noto Sans CJK SC", sans-serif;
    line-height: 1.6;
    color: #333;
}

body {
    string-set: title content();
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    font-family: "Noto Sans CJK SC", sans-serif;
}

h1 {
    font-size: 24pt;
    border-bottom: 2px solid #eee;
    padding-bottom: 0.5em;
}

h2 {
    font-size: 18pt;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.3em;
}

h3 {
    font-size: 14pt;
}

p {
    margin: 0.8em 0;
    text-align: justify;
}

pre, code {
    font-family: "Noto Sans Mono CJK SC", "Noto Sans Mono SC", monospace;
    background-color: #f5f5f5;
    border-radius: 4px;
    font-size: 10pt;
}

pre {
    padding: 1em;
    overflow-x: auto;
    border: 1px solid #e0e0e0;
    white-space: pre-wrap;
    word-wrap: break-word;
    word-break: break-all;
}

code {
    padding: 0.2em 0.4em;
    font-size: 90%;
}

blockquote {
    margin: 1em 0;
    padding: 0.5em 1em;
    border-left: 4px solid #0066ff;
    background-color: #f9f9f9;
    color: #666;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    page-break-inside: avoid;
}

ul, ol {
    padding-left: 2em;
    margin: 0.8em 0;
}

li {
    margin: 0.3em 0;
}

a {
    color: #0066ff;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* 版权声明样式 */
.copyright-notice {
    font-size: 9pt;
    color: #999;
    border-top: 1px solid #eee;
    padding-top: 1em;
    margin-top: 2em;
}
"""

# 简化版 CSS，强制使用字体
MINIMAL_CSS = """
@page {
    size: A4;
    margin: 2cm;
}

html {
    font-family: "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
    line-height: 1.6;
}

h1, h2, h3, h4, h5, h6, p, a, pre, code, blockquote, table, li, th, td {
    font-family: "Noto Sans CJK SC", "Source Han Sans SC", sans-serif !important;
}

pre {
    white-space: pre-wrap;
    word-wrap: break-word;
}

img {
    max-width: 100%;
    height: auto;
}
"""


class PDFConverter:
    """PDF 转换器"""

    def __init__(self, font_config: FontConfiguration = None):
        """
        初始化 PDF 转换器

        Args:
            font_config: 字体配置（用于字体 fallback）
        """
        self.font_config = font_config or FontConfiguration()

    def convert(
        self,
        html_content: str,
        output_path: str,
        title: str = "",
        base_url: str = None,
    ) -> bool:
        """
        将 HTML 转换为 PDF

        Args:
            html_content: HTML 内容
            output_path: 输出文件路径
            title: 文档标题（用于页眉）
            base_url: 基础 URL（用于解析相对路径）

        Returns:
            是否转换成功
        """
        try:
            # 添加文档标题
            if title:
                full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{title}</title>
                </head>
                <body>
                    <h1>{title}</h1>
                    {html_content}
                </body>
                </html>
                """
            else:
                full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 使用简化的 CSS 配置，强制嵌入字体
            css = CSS(string=MINIMAL_CSS, font_config=self.font_config)

            # 转换 PDF，嵌入所有字体
            html_doc = HTML(string=full_html, base_url=base_url)
            html_doc.write_pdf(
                output_path,
                stylesheets=[css],
                font_config=self.font_config,
            )

            logger.info(f"PDF 生成成功：{output_path}")
            return True

        except Exception as e:
            logger.error(f"PDF 转换失败：{str(e)}")
            return False

    def convert_with_images(
        self,
        html_content: str,
        output_path: str,
        image_dir: str = None,
        title: str = "",
    ) -> bool:
        """
        将带本地图片的 HTML 转换为 PDF

        Args:
            html_content: HTML 内容
            output_path: 输出文件路径
            image_dir: 图片目录（用于解析本地图片）
            title: 文档标题

        Returns:
            是否转换成功
        """
        base_url = f"file://{os.path.abspath(image_dir)}" if image_dir else None
        return self.convert(html_content, output_path, title, base_url)


def html_to_pdf(
    html_content: str,
    output_path: str,
    title: str = "",
    image_dir: str = None,
) -> bool:
    """
    便捷函数：HTML 转 PDF

    Args:
        html_content: HTML 内容
        output_path: 输出文件路径
        title: 文档标题
        image_dir: 图片目录

    Returns:
        是否转换成功
    """
    converter = PDFConverter()
    return converter.convert_with_images(html_content, output_path, image_dir, title)
