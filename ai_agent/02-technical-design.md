# 知乎收藏夹导出工具 - 技术设计方案

**文档版本**: v1.0
**创建时间**: 2026-03-13

---

## 1. 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI / Web UI                          │
├─────────────────────────────────────────────────────────────┤
│  auth/  │  crawler/  │  converter/  │  exporter/  │  storage/│
├─────────────────────────────────────────────────────────────┤
│                    核心依赖库                                │
│   httpx  │  BeautifulSoup  │  markdownify  │  weasyprint    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 模块设计

### 2.1 auth/ 授权模块

**文件**: `cookie_auth.py`, `encryptor.py`

```python
class AuthEncryptor:
    """加密器 - PBKDF2+FERNET"""
    - encrypt(data: dict) -> str
    - decrypt(encrypted: str) -> dict

class CookieAuth:
    """Cookie 管理"""
    - load_cookies() -> bool
    - save_cookies(cookies, user_id) -> bool
    - validate_cookies() -> bool
    - parse_cookie_string(str) -> dict
```

### 2.2 crawler/ 抓取模块

**文件**: `fetcher.py`

```python
class ZhihuFetcher:
    """内容抓取器"""
    - get_collection_urls(id) -> (urls, titles)
    - get_single_answer_content(url) -> html
    - get_single_post_content(url) -> html
    - fetch_collection_list() -> list
```

### 2.3 converter/ 转换模块

**文件**: `markdown.py`, `pdf.py`

```python
class ObsidianStyleConverter(MarkdownConverter):
    """Markdown 转换器"""
    - convert_img() -> 本地引用
    - convert_a() -> 链接处理

class PDFConverter:
    """PDF 转换器"""
    - convert(html, output_path) -> bool
```

### 2.4 cli/ 命令行模块

**文件**: `main.py`

```
命令:
  auth          - Cookie 授权
  list          - 列出收藏夹
  export        - 导出收藏夹
```

---

## 3. 目录结构

```
zhihu_download/
├── ai_agent/              # AI Agent 文档
│   ├── 01-requirements.md
│   ├── 02-technical-design.md
│   └── 03-progress-log.md
├── src/
│   ├── auth/              # 授权模块
│   ├── crawler/           # 抓取模块
│   ├── converter/         # 转换模块
│   └── ...
├── cli/
│   └── main.py            # CLI 入口
├── requirements.txt       # 依赖清单
└── README.md              # 使用说明
```

---

## 4. 关键实现

### 4.1 Cookie 加密存储

```python
# 盐值存储在 ~/.zhihu_download/.salt
# Cookie 加密存储在 ~/.zhihu_download/.cookies.encrypted
# 使用 PBKDF2HMAC 推导密钥，FERNET 加密
```

### 4.2 请求延迟控制

```python
def _delay(self):
    delay_ms = random.randint(1000, 2000)  # 1-2 秒
    time.sleep(delay_ms / 1000)
```

### 4.3 HTML 解析

```python
# 多重选择器兜底
selectors = [
    ("div", {"class": "AnswerCard"}),
    ("div", {"class": "QuestionAnswer-content"}),
    ("div", {"class": "RichContent"}),
]
```

### 4.4 Markdown 转换

```python
# 图片下载到 assets/ 目录
# 返回 Obsidian 风格：![[image.png]](alt)
```

### 4.5 PDF 渲染

```python
# weasyprint + 中文字体配置
# A4 页面，页眉页脚，版权声明
```

---

## 5. 依赖清单

```
httpx>=0.25.0          # HTTP 客户端
beautifulsoup4>=4.12.0 # HTML 解析
lxml>=4.9.0            # XML/HTML 解析
markdownify>=0.11.0    # HTML 转 Markdown
weasyprint>=60.0       # PDF 生成
typer>=0.9.0           # CLI 框架
rich>=13.0.0           # 终端美化
cryptography>=41.0.0   # 加密
```

---

## 6. 已完成功能

- [x] Web UI 界面 (FastAPI + 原生 JS)
- [x] MCP Skill 接口
- [x] HTML 单文件格式
- [x] CSV 台账导出
- [x] 增量导出
- [x] 断点续传
- [x] ZIP 压缩打包
