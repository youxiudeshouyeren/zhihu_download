# -*- coding:utf-8 -*-
"""
日志系统模块
提供统一的日志配置和管理
"""
import os
import logging
from datetime import datetime
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    log_filename: Optional[str] = None
) -> str:
    """
    配置日志系统
    :param log_dir: 日志目录
    :param log_level: 文件日志级别
    :param console_level: 控制台日志级别
    :param log_filename: 日志文件名（可选）
    :return: 日志文件路径
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件名
    if log_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"zhihu_export_{timestamp}.log"

    log_path = os.path.join(log_dir, log_filename)

    # 清除已有处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建文件处理器
    file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
    file_handler.setLevel(log_level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)

    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 测试日志
    logging.info(f"日志系统初始化完成，日志文件：{log_path}")

    return log_path


def get_logger(name: str) -> logging.Logger:
    """
    获取命名日志器
    :param name: 日志器名称
    :return: 日志器实例
    """
    return logging.getLogger(name)
