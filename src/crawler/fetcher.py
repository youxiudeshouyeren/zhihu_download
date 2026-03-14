# -*- coding: utf-8 -*-
"""内容抓取模块 - 复用现有项目逻辑"""

import random
import time
import logging
from typing import List, Tuple, Optional, Dict, Any
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)


class ZhihuFetcher:
    """知乎内容抓取类"""

    def __init__(self, cookies: Dict[str, str], request_delay_range: Tuple[int, int] = (1000, 2000)):
        """
        初始化抓取器

        Args:
            cookies: Cookie 字典
            request_delay_range: 请求延迟范围（毫秒）
        """
        self.cookies = cookies
        self.request_delay_range = request_delay_range
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Connection": "keep-alive",
            "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8",
        }
        self._client = httpx.Client(cookies=cookies, headers=self.headers, timeout=30)

    def _delay(self):
        """随机延迟"""
        delay_ms = random.randint(self.request_delay_range[0], self.request_delay_range[1])
        time.sleep(delay_ms / 1000)

    def get_collection_item_count(self, collection_id: str) -> int:
        """
        获取收藏夹内容总数

        Args:
            collection_id: 收藏夹 ID

        Returns:
            内容总数
        """
        try:
            url = f"https://www.zhihu.com/api/v4/collections/{collection_id}/items"
            response = self._client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("paging", {}).get("totals", 0)
        except Exception as e:
            logger.error(f"获取收藏夹 {collection_id} 总数失败：{str(e)}")
            return 0

    def get_collection_urls(self, collection_id: str) -> Tuple[List[str], List[str]]:
        """
        获取收藏夹内所有内容的 URL 和标题

        Args:
            collection_id: 收藏夹 ID

        Returns:
            (URL 列表，标题列表)
        """
        logger.info(f"开始获取收藏夹 {collection_id} 的文章列表")

        offset = 0
        limit = 20
        item_count = self.get_collection_item_count(collection_id)

        if item_count == 0:
            logger.warning(f"收藏夹 {collection_id} 没有文章或获取失败")
            return [], []

        url_list = []
        title_list = []

        while offset < item_count:
            url = f"https://www.zhihu.com/api/v4/collections/{collection_id}/items?offset={offset}&limit={limit}"
            try:
                logger.info(f"请求收藏夹 API: offset={offset}, limit={limit}")
                response = self._client.get(url)
                response.raise_for_status()
                content = response.json()
                logger.info(f"成功获取 {len(content.get('data', []))} 个项目")
            except Exception as e:
                logger.error(f"请求收藏夹 API 失败：{str(e)}")
                return url_list, title_list

            for el in content.get("data", []):
                try:
                    url_list.append(el["content"]["url"])
                    if el["content"]["type"] == "answer":
                        title_list.append(el["content"]["question"]["title"])
                    else:
                        title_list.append(el["content"].get("title", "未知标题"))
                    logger.debug(f"添加文章：{el['content'].get('title', '未知标题')}")
                except Exception as e:
                    logger.warning(f"解析文章项目失败：{str(e)}")
                    # 如果已经添加了 URL，需要移除对应的 URL
                    if len(url_list) > len(title_list):
                        url_list.pop()

            offset += limit
            self._delay()

        logger.info(f"收藏夹 {collection_id} 总共获取到 {len(url_list)} 个有效文章")
        return url_list, title_list

    def fetch_collection_list(self, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        从知乎收藏夹页面获取用户所有收藏夹列表（页面解析方式）

        Args:
            cookies: Cookie 字典（可选，默认使用实例的 cookies）

        Returns:
            收藏夹列表，每项包含 id, title, creator, count, url
        """
        cookies = cookies or self.cookies
        all_collections = []
        page = 1

        while True:
            url = f"https://www.zhihu.com/collections/mine?page={page}"

            try:
                response = httpx.get(
                    url,
                    cookies=cookies,
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                # 查找所有的 SelfCollectionItem
                collection_items = soup.find_all(class_="SelfCollectionItem")

                if not collection_items:
                    logger.info(f"第{page}页没有更多收藏夹，结束获取")
                    break

                for item in collection_items:
                    # 查找标题元素
                    title_element = item.find(class_="SelfCollectionItem-title")
                    if title_element:
                        # 获取收藏夹名称
                        name = title_element.get_text(strip=True)

                        # 获取 href 链接
                        link_element = title_element.find("a")
                        if link_element and link_element.get("href"):
                            href = link_element.get("href")
                            # 从 URL 中提取收藏夹 ID
                            collection_id = href.rstrip("/").split("/")[-1]

                            # 获取创建者和内容数（如果有的话）
                            creator_element = item.find(class_="SelfCollectionItem-creator")
                            creator = creator_element.get_text(strip=True) if creator_element else "未知"

                            count_element = item.find(class_="SelfCollectionItem-count")
                            count_text = count_element.get_text(strip=True) if count_element else "0"
                            # 提取数字
                            try:
                                count = int(count_text)
                            except ValueError:
                                count = 0

                            all_collections.append({
                                "id": collection_id,
                                "title": name,
                                "creator": {"name": creator},
                                "count": count,
                                "url": f"https://www.zhihu.com{href}" if href.startswith("/") else href
                            })

                logger.info(f"第{page}页获取到 {len(collection_items)} 个收藏夹")
                page += 1
                time.sleep(random.randint(1, 3))

            except Exception as e:
                logger.error(f"获取第{page}页收藏夹失败：{str(e)}")
                break

        logger.info(f"总共获取到 {len(all_collections)} 个收藏夹")
        return all_collections

    def get_single_answer_content(self, answer_url: str) -> Optional[str]:
        """
        获取单个回答的 HTML 内容

        Args:
            answer_url: 回答 URL

        Returns:
            回答的 HTML 内容，失败返回 None
        """
        logger.debug(f"开始获取回答内容：{answer_url}")

        try:
            response = self._client.get(answer_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # 尝试多种选择器
            selectors = [
                ("div", {"class": "AnswerCard"}),
                ("div", {"class": "QuestionAnswer-content"}),
                ("div", {"class": "RichContent"}),
            ]

            answer_content = None
            for tag, attrs in selectors:
                elements = soup.find_all(tag, attrs)
                if elements:
                    for element in elements:
                        inner = element.find("div", class_="RichContent-inner")
                        if inner:
                            answer_content = inner
                            break
                    if answer_content:
                        break

            # 备用选择器
            if not answer_content:
                fallback_selectors = [
                    "div.RichText",
                    "div.Post-RichText",
                    "div.ContentItem-content",
                ]
                for selector in fallback_selectors:
                    answer_content = soup.select_one(selector)
                    if answer_content:
                        break

            if not answer_content:
                logger.error(f"未找到回答内容容器：{answer_url}")
                return None

            # 清理不需要的元素
            for el in answer_content.find_all("style"):
                el.extract()

            for el in answer_content.select('img[src*="data:image/svg+xml"]'):
                el.extract()

            # 处理链接卡片
            for el in answer_content.find_all("a"):
                aclass = el.get("class")
                if isinstance(aclass, list) and aclass and aclass[0] == "LinkCard":
                    linkcard_name = el.get("data-text")
                    el.string = linkcard_name if linkcard_name else el.get("href")
                try:
                    if el.get("href", "").startswith("mailto"):
                        el.name = "p"
                except:
                    pass

            return str(answer_content)

        except Exception as e:
            logger.error(f"获取回答内容时发生错误：{str(e)}")
            return None

    def get_single_post_content(self, post_url: str) -> Optional[str]:
        """
        获取单个专栏文章的 HTML 内容

        Args:
            post_url: 专栏文章 URL

        Returns:
            文章的 HTML 内容，失败返回 None
        """
        logger.debug(f"开始获取专栏文章内容：{post_url}")

        try:
            response = self._client.get(post_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # 尝试多种选择器
            selectors = [
                ("div", {"class": "Post-RichText"}),
                ("div", {"class": "RichContent"}),
                ("div", {"class": "Post-content"}),
                ("div", {"class": "Post-RichTextContainer"}),
            ]

            post_content = None
            for tag, attrs in selectors:
                post_content = soup.find(tag, attrs)
                if post_content:
                    break

            # 备用选择器
            if not post_content:
                fallback_selectors = [
                    "div.RichText",
                    "div.Post-content",
                    "div.ContentItem-content",
                ]
                for selector in fallback_selectors:
                    post_content = soup.select_one(selector)
                    if post_content:
                        break

            if not post_content:
                logger.error(f"未找到专栏内容容器：{post_url}")
                return None

            # 清理不需要的元素
            for el in post_content.find_all("style"):
                el.extract()

            for el in post_content.select('img[src*="data:image/svg+xml"]'):
                el.extract()

            # 处理链接卡片
            for el in post_content.find_all("a"):
                aclass = el.get("class")
                if isinstance(aclass, list) and aclass and aclass[0] == "LinkCard":
                    linkcard_name = el.get("data-text")
                    el.string = linkcard_name if linkcard_name else el.get("href")
                try:
                    if el.get("href", "").startswith("mailto"):
                        el.name = "p"
                except:
                    pass

            return str(post_content)

        except Exception as e:
            logger.error(f"获取专栏文章内容时发生错误：{str(e)}")
            return None
