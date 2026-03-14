# -*- coding: utf-8 -*-
"""增量导出/断点续传模块"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, Any, List

logger = logging.getLogger(__name__)


class ExportProgress:
    """导出进度追踪器"""

    def __init__(self, collection_id: str, output_dir: str):
        """
        初始化导出进度追踪器

        Args:
            collection_id: 收藏夹 ID
            output_dir: 输出目录
        """
        self.collection_id = collection_id
        self.output_dir = output_dir
        self.progress_file = os.path.join(
            output_dir, f"collection_{collection_id}", ".export_progress.json"
        )
        self.progress_data = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        """加载进度文件"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载进度文件失败：{str(e)}")

        return {
            "collection_id": None,
            "started_at": None,
            "updated_at": None,
            "total": 0,
            "exported": [],
            "failed": [],
            "status": "pending"
        }

    def save_progress(self):
        """保存进度"""
        self.progress_data["updated_at"] = datetime.now().isoformat()

        # 确保目录存在
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)

        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress_data, f, ensure_ascii=False, indent=2)

    def start(self, total: int):
        """开始导出"""
        self.progress_data["started_at"] = datetime.now().isoformat()
        self.progress_data["total"] = total
        self.progress_data["status"] = "running"
        self.save_progress()

    def mark_exported(self, url: str, title: str):
        """标记文章已导出"""
        exported_item = {
            "url": url,
            "title": title,
            "exported_at": datetime.now().isoformat()
        }

        # 检查是否已存在
        for i, item in enumerate(self.progress_data["exported"]):
            if item["url"] == url:
                self.progress_data["exported"][i] = exported_item
                self.save_progress()
                return False  # 不是新增的

        self.progress_data["exported"].append(exported_item)
        self.save_progress()
        return True  # 新增的

    def mark_failed(self, url: str, title: str, error: str):
        """标记文章导出失败"""
        failed_item = {
            "url": url,
            "title": title,
            "error": error,
            "failed_at": datetime.now().isoformat()
        }

        # 检查是否已存在
        for i, item in enumerate(self.progress_data["failed"]):
            if item["url"] == url:
                self.progress_data["failed"][i] = failed_item
                self.save_progress()
                return

        self.progress_data["failed"].append(failed_item)
        self.save_progress()

    def is_exported(self, url: str) -> bool:
        """检查文章是否已导出"""
        for item in self.progress_data["exported"]:
            if item["url"] == url:
                return True
        return False

    def get_exported_urls(self) -> Set[str]:
        """获取已导出的 URL 集合"""
        return {item["url"] for item in self.progress_data["exported"]}

    def get_failed_urls(self) -> Set[str]:
        """获取失败过的 URL 集合"""
        return {item["url"] for item in self.progress_data["failed"]}

    def complete(self):
        """标记导出完成"""
        self.progress_data["status"] = "completed"
        self.progress_data["completed_at"] = datetime.now().isoformat()
        self.save_progress()

    def fail(self, error: str):
        """标记导出失败"""
        self.progress_data["status"] = "failed"
        self.progress_data["error"] = error
        self.progress_data["failed_at"] = datetime.now().isoformat()
        self.save_progress()

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "total": self.progress_data["total"],
            "exported": len(self.progress_data["exported"]),
            "failed": len(self.progress_data["failed"]),
            "remaining": self.progress_data["total"] - len(self.progress_data["exported"]) - len(self.progress_data["failed"])
        }

    def should_resume(self) -> bool:
        """是否可以恢复导出"""
        if self.progress_data["status"] == "completed":
            return False
        if self.progress_data["status"] == "running":
            # 如果是运行中中断的，可以恢复
            return True
        return False

    def clear(self):
        """清除进度记录"""
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        self.progress_data = {
            "collection_id": None,
            "started_at": None,
            "updated_at": None,
            "total": 0,
            "exported": [],
            "failed": [],
            "status": "pending"
        }


class ContentDeduplicator:
    """内容去重器"""

    def __init__(self, output_dir: str):
        """
        初始化内容去重器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.index_file = os.path.join(output_dir, ".content_index.json")
        self.index_data = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """加载内容索引"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载内容索引失败：{str(e)}")

        return {
            "updated_at": None,
            "contents": {}  # url -> {title, file_path, exported_at, content_hash}
        }

    def save_index(self):
        """保存内容索引"""
        self.index_data["updated_at"] = datetime.now().isoformat()

        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index_data, f, ensure_ascii=False, indent=2)

    def add_content(self, url: str, title: str, file_path: str, content_hash: str = None):
        """
        添加内容到索引

        Args:
            url: 内容 URL
            title: 标题
            file_path: 文件路径
            content_hash: 内容哈希（可选）
        """
        self.index_data["contents"][url] = {
            "title": title,
            "file_path": file_path,
            "exported_at": datetime.now().isoformat(),
            "content_hash": content_hash
        }
        self.save_index()

    def is_duplicate(self, url: str) -> bool:
        """检查内容是否已存在"""
        return url in self.index_data["contents"]

    def get_content_info(self, url: str) -> Dict[str, Any]:
        """获取内容信息"""
        return self.index_data["contents"].get(url, {})

    def get_all_urls(self) -> List[str]:
        """获取所有已索引的 URL"""
        return list(self.index_data["contents"].keys())

    def remove_content(self, url: str):
        """移除内容索引"""
        if url in self.index_data["contents"]:
            del self.index_data["contents"][url]
            self.save_index()

    def find_duplicates_by_title(self, title: str) -> List[str]:
        """根据标题查找重复内容"""
        duplicates = []
        for url, info in self.index_data["contents"].items():
            if info.get("title") == title:
                duplicates.append(url)
        return duplicates

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "total_contents": len(self.index_data["contents"]),
            "unique_titles": len(set(info.get("title", "") for info in self.index_data["contents"].values()))
        }
