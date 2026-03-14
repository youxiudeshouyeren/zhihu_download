# -*- coding: utf-8 -*-
"""Markdown 转换模块 - 复用现有项目逻辑"""

import logging
import requests
import os
import re
from markdownify import MarkdownConverter, chomp
from typing import Optional

logger = logging.getLogger(__name__)


class ObsidianStyleConverter(MarkdownConverter):
    """
    自定义 Markdown 转换器，支持图片本地化下载
    """

    def __init__(self, *args, **kwargs):
        self.headers = kwargs.pop("headers", {})
        self.cookies = kwargs.pop("cookies", {})
        self.download_dir = kwargs.pop("download_dir", None)
        self.article_title = kwargs.pop("article_title", "default")
        super().__init__(*args, **kwargs)
        # 创建文章专属的图片目录
        self.assets_dir = self._get_assets_dir()

    def _get_assets_dir(self) -> str:
        """获取文章专属的图片目录"""
        if not self.download_dir:
            return None
        # 清理标题中的非法字符
        safe_title = re.sub(r'[\\/"<>|:*?]', '_', self.article_title)[:50]
        assets_dir = os.path.join(self.download_dir, "assets", safe_title)
        os.makedirs(assets_dir, exist_ok=True)
        return assets_dir

    def convert_img(self, el, text, parent_tags=None):
        """转换图片为本地引用"""
        try:
            alt = el.attrs.get("alt", "") or ""
            src = el.attrs.get("src", None) or ""

            # 跳过 SVG 占位图
            if "data:image/svg+xml" in src:
                return ""

            # 下载图片到本地
            if self.assets_dir and src:
                try:
                    img_name = src.split("?")[0].split("/")[-1]
                    # 如果文件名太长，截断
                    if len(img_name) > 100:
                        img_name = img_name[:50] + img_name[-40:]
                    img_path = os.path.join(self.assets_dir, img_name)

                    if not os.path.exists(img_path):
                        response = requests.get(url=src, headers=self.headers, cookies=self.cookies)
                        with open(img_path, "wb") as fp:
                            fp.write(response.content)

                    # 返回标准 Markdown 图片引用（相对路径）
                    relative_path = os.path.join("assets", self.article_title, img_name)
                    # 使用正斜杠
                    relative_path = relative_path.replace("\\", "/")
                    return f"![]({relative_path})\n\n"
                except Exception as e:
                    logger.error(f"下载图片失败：{src}, 错误：{str(e)}")
                    return f"![{alt}]({src})\n\n"

            return f"![{alt}]({src})\n\n"
        except Exception as e:
            logger.error(f"convert_img error: {str(e)}")
            return ""

    def convert_a(self, el, text, parent_tags=None):
        """转换链接"""
        # 处理特殊链接类型
        if el.get("aria-labelledby") and "ref" in el.get("aria-labelledby", ""):
            return text.replace("[", "[^")

        if el.get("class") and any("ReferenceList-backLink" in c for c in el.get("class", [])):
            return f"[^{el.get('href', '')[5:]}]: "

        # 调用父类方法
        return super().convert_a(el, text, parent_tags)


def html_to_markdown(html: str, download_dir: str = None, headers: dict = None,
                     cookies: dict = None, article_title: str = "default") -> str:
    """
    将 HTML 转换为 Markdown

    Args:
        html: HTML 字符串
        download_dir: 图片下载目录
        headers: 请求头
        cookies: Cookie
        article_title: 文章标题（用于创建专属图片目录）

    Returns:
        Markdown 字符串
    """
    converter = ObsidianStyleConverter(
        heading_style="ATX",
        download_dir=download_dir,
        headers=headers or {},
        cookies=cookies or {},
        article_title=article_title,
    )
    return converter.convert(html)
