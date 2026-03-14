# -*- coding: utf-8 -*-
"""工具函数模块"""

import re
import os


def safe_filename(title: str, max_length: int = 50) -> str:
    """
    将标题转换为安全的文件名

    Args:
        title: 原始标题
        max_length: 最大长度

    Returns:
        安全的文件名字符串
    """
    # 过滤非法字符：\ / : * ? " < > |
    safe = re.sub(r'[\\\/:*?"<>|]', '_', title)

    # 替换连续的空格为单个下划线
    safe = re.sub(r'\s+', '_', safe)

    # 移除开头和结尾的特殊字符
    safe = safe.strip('_.- ')

    # 截断到最大长度
    if len(safe) > max_length:
        safe = safe[:max_length]

    # 如果结果为空，返回默认值
    if not safe:
        safe = 'default'

    return safe


def ensure_dir(path: str) -> str:
    """
    确保目录存在，如不存在则创建

    Args:
        path: 目录路径

    Returns:
        目录路径
    """
    os.makedirs(path, exist_ok=True)
    return path


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    格式化时间 duration

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分"


def is_valid_zhihu_url(url: str) -> bool:
    """
    检查是否为有效的知乎 URL

    Args:
        url: URL 字符串

    Returns:
        是否有效
    """
    patterns = [
        r'^https?://(www\.)?zhihu\.com/question/',  # 问题
        r'^https?://(www\.)?zhihu\.com/collection/',  # 收藏夹
        r'^https?://zhuanlan\.zhihu\.com/p/',  # 专栏文章
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def extract_collection_id(url: str) -> str:
    """
    从知乎收藏夹 URL 中提取 ID

    Args:
        url: 收藏夹 URL

    Returns:
        收藏夹 ID
    """
    match = re.search(r'collection/(\d+)', url)
    if match:
        return match.group(1)
    return ''


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
