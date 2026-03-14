# -*- coding: utf-8 -*-
"""授权信息加密存储模块"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class AuthEncryptor:
    """授权信息加密存储类"""

    def __init__(self, password: str = None):
        """
        初始化解密器

        Args:
            password: 用于生成加密密钥的密码，如不提供则使用默认值
        """
        self._password = password or "zhihu_download_default_key"
        self._salt = self._get_or_create_salt()
        self._fernet = self._create_fernet()

    def _get_salt_path(self) -> str:
        """获取盐文件路径"""
        config_dir = os.path.join(os.path.expanduser("~"), ".zhihu_download")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, ".salt")

    def _get_or_create_salt(self) -> bytes:
        """获取或创建盐值"""
        salt_path = self._get_salt_path()

        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
            return salt

    def _create_fernet(self) -> Fernet:
        """创建 Fernet 加密实例"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._password.encode()))
        return Fernet(key)

    def encrypt(self, data: dict) -> str:
        """
        加密字典数据

        Args:
            data: 待加密的字典数据

        Returns:
            加密后的 base64 字符串
        """
        json_str = json.dumps(data, ensure_ascii=False)
        encrypted = self._fernet.encrypt(json_str.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, encrypted_str: str) -> dict:
        """
        解密字符串数据

        Args:
            encrypted_str: 加密后的 base64 字符串

        Returns:
            解密后的字典数据
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_str.encode("utf-8"))
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"解密失败：{str(e)}")

    def clear(self):
        """清除盐值（用于一键清除授权信息）"""
        salt_path = self._get_salt_path()
        if os.path.exists(salt_path):
            os.remove(salt_path)
