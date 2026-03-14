# -*- coding: utf-8 -*-
"""ZIP 压缩打包模块"""

import os
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


def zip_directory(
    source_dir: str,
    output_zip: str = None,
    compression: int = zipfile.ZIP_DEFLATED,
    exclude_patterns: Optional[List[str]] = None,
    include_timestamp: bool = True
) -> str:
    """
    将整个目录压缩为 ZIP 文件

    Args:
        source_dir: 源目录路径
        output_zip: 输出 ZIP 文件路径（可选，默认为源目录名.zip）
        compression: 压缩方式，默认 ZIP_DEFLATED
        exclude_patterns: 排除的文件模式列表，如 ['.log', '.tmp', '__pycache__']
        include_timestamp: 是否在 ZIP 文件名中包含时间戳

    Returns:
        生成的 ZIP 文件路径
    """
    source_path = Path(source_dir).resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"源目录不存在：{source_dir}")

    if not source_path.is_dir():
        raise ValueError(f"源路径不是目录：{source_dir}")

    # 确定输出文件名
    if output_zip is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if include_timestamp else ""
        zip_name = f"{source_path.name}_{timestamp}.zip" if include_timestamp else f"{source_path.name}.zip"
        output_zip = str(source_path.parent / zip_name)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_zip), exist_ok=True)

    # 排除模式
    if exclude_patterns is None:
        exclude_patterns = ['.log', '.tmp', '.pyc', '__pycache__', '.git', '.DS_Store']

    excluded_count = 0
    total_files = 0
    compressed_files = 0

    with zipfile.ZipFile(output_zip, 'w', compression=compression) as zipf:
        for root, dirs, files in os.walk(source_path):
            # 过滤目录
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]

            for file in files:
                total_files += 1
                file_path = Path(root) / file

                # 检查是否应该排除
                if any(file.endswith(pattern) for pattern in exclude_patterns):
                    excluded_count += 1
                    continue

                # 计算在 ZIP 中的相对路径
                arc_name = str(file_path.relative_to(source_path))

                try:
                    zipf.write(file_path, arc_name)
                    compressed_files += 1
                    logger.debug(f"添加到 ZIP: {arc_name}")
                except Exception as e:
                    logger.error(f"压缩文件失败：{file_path}, 错误：{str(e)}")

    # 获取压缩后的大小
    original_size = sum(
        (Path(root) / file).stat().st_size
        for root, dirs, files in os.walk(source_path)
        for file in files
        if not any(file.endswith(p) for p in exclude_patterns)
    )

    compressed_size = Path(output_zip).stat().st_size
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

    logger.info(f"压缩完成：{output_zip}")
    logger.info(f"  原始文件数：{total_files}")
    logger.info(f"  压缩文件数：{compressed_files}")
    logger.info(f"  排除文件数：{excluded_count}")
    logger.info(f"  原始大小：{format_size(original_size)}")
    logger.info(f"  压缩后大小：{format_size(compressed_size)}")
    logger.info(f"  压缩率：{compression_ratio:.1f}%")

    return output_zip


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def create_collection_zip(
    collection_id: str,
    output_dir: str,
    formats: Optional[List[str]] = None,
    include_metadata: bool = True,
    include_timestamp: bool = True
) -> str:
    """
    为收藏夹创建 ZIP 压缩包

    Args:
        collection_id: 收藏夹 ID
        output_dir: 输出目录
        formats: 包含的格式列表（如 ['md', 'pdf']），None 表示包含所有
        include_metadata: 是否包含元数据文件
        include_timestamp: 是否包含时间戳

    Returns:
        ZIP 文件路径
    """
    collection_dir = os.path.join(output_dir, f"collection_{collection_id}")

    if not os.path.exists(collection_dir):
        raise FileNotFoundError(f"收藏夹目录不存在：{collection_dir}")

    # 排除模式
    exclude_patterns = ['.log', '.tmp', '.pyc', '__pycache__', '.DS_Store']

    # 如果指定了格式，排除其他格式
    if formats:
        all_formats = ['md', 'pdf', 'html', 'csv']
        for fmt in all_formats:
            if fmt not in formats:
                exclude_patterns.append(f'/{fmt}/')

    # 排除进度文件
    if not include_metadata:
        exclude_patterns.extend(['.export_progress.json', '.content_index.json', '_metadata.csv'])

    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if include_timestamp else ""
    zip_name = f"collection_{collection_id}_{timestamp}.zip" if include_timestamp else f"collection_{collection_id}.zip"
    output_zip = os.path.join(output_dir, zip_name)

    return zip_directory(
        collection_dir,
        output_zip,
        exclude_patterns=exclude_patterns,
        include_timestamp=False  # 已经在文件名中处理
    )


def extract_zip(
    zip_path: str,
    dest_dir: str,
    password: Optional[str] = None
) -> List[str]:
    """
    解压 ZIP 文件

    Args:
        zip_path: ZIP 文件路径
        dest_dir: 目标目录
        password: 解压密码（可选）

    Returns:
        解压的文件列表
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP 文件不存在：{zip_path}")

    os.makedirs(dest_dir, exist_ok=True)

    extracted_files = []

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        # 如果有密码，设置密码
        if password:
            zipf.setpassword(password.encode('utf-8'))

        # 解压所有文件
        zipf.extractall(dest_dir)

        # 获取文件列表
        extracted_files = zipf.namelist()

    logger.info(f"解压完成：{zip_path} -> {dest_dir}")
    logger.info(f"  解压文件数：{len(extracted_files)}")

    return extracted_files


def list_zip_contents(zip_path: str) -> List[str]:
    """
    列出 ZIP 文件内容

    Args:
        zip_path: ZIP 文件路径

    Returns:
        文件列表
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP 文件不存在：{zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        return zipf.namelist()


def get_zip_info(zip_path: str) -> dict:
    """
    获取 ZIP 文件信息

    Args:
        zip_path: ZIP 文件路径

    Returns:
        ZIP 文件信息字典
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP 文件不存在：{zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        info_list = zipf.infolist()

        total_files = len(info_list)
        total_size = sum(info.file_size for info in info_list)
        compressed_size = sum(info.compress_size for info in info_list)

        # 获取修改时间
        latest_mod = max(info.date_time for info in info_list)

        return {
            "path": zip_path,
            "total_files": total_files,
            "total_size": total_size,
            "compressed_size": compressed_size,
            "compression_ratio": (1 - compressed_size / total_size) * 100 if total_size > 0 else 0,
            "latest_modification": f"{latest_mod[0]}-{latest_mod[1]:02d}-{latest_mod[2]:02d} {latest_mod[3]}:{latest_mod[4]:02d}"
        }
