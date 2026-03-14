# -*- coding: utf-8 -*-
"""CSV 转换模块 - 导出结构化台账"""

import logging
import csv
import os
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVConverter:
    """CSV 转换器"""

    # CSV 字段名
    FIELDNAMES = [
        'id',
        'title',
        'author',
        'content_type',
        'original_url',
        'published_time',
        'collected_time',
        'collection_name',
        'upvotes',
        'comments',
        'is_invalid',
        'is_premium',
        'export_time',
        'file_path'
    ]

    def convert(
        self,
        items: List[Dict[str, Any]],
        output_path: str,
        collection_name: str = ""
    ) -> bool:
        """
        将内容列表转换为 CSV 台账

        Args:
            items: 内容项列表，每项包含元数据
            output_path: 输出文件路径
            collection_name: 收藏夹名称

        Returns:
            是否转换成功
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            export_time = datetime.now().isoformat()

            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

                for item in items:
                    row = {
                        'id': item.get('content_id', ''),
                        'title': item.get('title', ''),
                        'author': item.get('author', {}).get('name', ''),
                        'content_type': item.get('content_type', ''),
                        'original_url': item.get('original_url', ''),
                        'published_time': item.get('published_time', ''),
                        'collected_time': item.get('collected_time', ''),
                        'collection_name': collection_name,
                        'upvotes': item.get('stats', {}).get('upvotes', 0),
                        'comments': item.get('stats', {}).get('comments', 0),
                        'is_invalid': item.get('is_invalid', False),
                        'is_premium': item.get('is_premium', False),
                        'export_time': export_time,
                        'file_path': item.get('exported_file', '')
                    }
                    writer.writerow(row)

            logger.info(f"CSV 台账生成成功：{output_path}")
            return True

        except Exception as e:
            logger.error(f"CSV 转换失败：{str(e)}")
            return False


def export_to_csv(
    items: List[Dict[str, Any]],
    output_path: str,
    collection_name: str = ""
) -> bool:
    """
    便捷函数：导出内容为 CSV 台账

    Args:
        items: 内容项列表
        output_path: 输出文件路径
        collection_name: 收藏夹名称

    Returns:
        是否转换成功
    """
    converter = CSVConverter()
    return converter.convert(items, output_path, collection_name)
