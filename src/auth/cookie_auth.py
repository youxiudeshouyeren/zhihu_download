# -*- coding: utf-8 -*-
"""Cookie 授权模块"""

import os
import json
import httpx
from typing import Optional, Dict, List
from .encryptor import AuthEncryptor


class CookieAuth:
    """Cookie 授权管理类"""

    def __init__(self):
        """初始化 Cookie 授权"""
        self._encryptor = AuthEncryptor()
        self._cookies_file = self._get_cookies_file_path()
        self._cookies: Dict[str, str] = {}
        self._user_id: Optional[str] = None

    def _get_cookies_file_path(self) -> str:
        """获取 cookies 文件路径"""
        config_dir = os.path.join(os.path.expanduser("~"), ".zhihu_download")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, ".cookies.encrypted")

    def load_cookies(self) -> bool:
        """
        从加密文件加载 Cookie

        Returns:
            是否加载成功
        """
        if not os.path.exists(self._cookies_file):
            return False

        try:
            with open(self._cookies_file, "r", encoding="utf-8") as f:
                encrypted_data = f.read()
            data = self._encryptor.decrypt(encrypted_data)
            self._cookies = data.get("cookies", {})
            self._user_id = data.get("user_id")
            return True
        except Exception as e:
            print(f"加载 Cookie 失败：{str(e)}")
            return False

    def save_cookies(self, cookies: Dict[str, str], user_id: str = None) -> bool:
        """
        保存 Cookie 到加密文件

        Args:
            cookies: Cookie 字典
            user_id: 用户 ID（可选）

        Returns:
            是否保存成功
        """
        try:
            data = {"cookies": cookies, "user_id": user_id}
            encrypted = self._encryptor.encrypt(data)
            with open(self._cookies_file, "w", encoding="utf-8") as f:
                f.write(encrypted)
            self._cookies = cookies
            self._user_id = user_id
            return True
        except Exception as e:
            print(f"保存 Cookie 失败：{str(e)}")
            return False

    def clear_cookies(self) -> bool:
        """
        清除保存的 Cookie

        Returns:
            是否清除成功
        """
        try:
            if os.path.exists(self._cookies_file):
                os.remove(self._cookies_file)
            self._cookies = {}
            self._user_id = None
            return True
        except Exception as e:
            print(f"清除 Cookie 失败：{str(e)}")
            return False

    def get_cookies(self) -> Dict[str, str]:
        """获取当前 Cookie"""
        return self._cookies.copy()

    def get_user_id(self) -> Optional[str]:
        """获取用户 ID"""
        return self._user_id

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return bool(self._cookies)

    def validate_cookies(self) -> bool:
        """
        验证 Cookie 是否有效

        Returns:
            Cookie 是否有效
        """
        if not self._cookies:
            return False

        try:
            # 访问知乎首页验证 Cookie
            response = httpx.get(
                "https://www.zhihu.com/api/v4/me",
                cookies=self._cookies,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                },
                timeout=10,
            )
            if response.status_code == 200:
                user_data = response.json()
                self._user_id = user_data.get("id") or user_data.get("url_token")
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
        """
        解析 Cookie 字符串为字典

        Args:
            cookie_str: Cookie 字符串（如 "a=1; b=2; c=3"）

        Returns:
            Cookie 字典
        """
        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookies[key.strip()] = value.strip()
        return cookies

    @staticmethod
    def load_from_json(json_path: str) -> Optional[Dict[str, str]]:
        """
        从 JSON 文件加载 Cookie 列表

        Args:
            json_path: JSON 文件路径，格式为 [{"name": "a", "value": "1"}, ...]

        Returns:
            Cookie 字典，加载失败返回 None
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cookies_list = json.load(f)
            return {c["name"]: c["value"] for c in cookies_list}
        except Exception:
            return None
