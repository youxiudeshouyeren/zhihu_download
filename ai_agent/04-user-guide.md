# 知乎收藏夹导出工具 - 用户使用指南

**文档版本**: v1.1
**最后更新**: 2026-03-14

---

## 目录

1. [快速开始](#1-快速开始)
2. [CLI 命令行使用](#2-cli-命令行使用)
3. [Web UI 使用](#3-web-ui-使用)
4. [MCP Skill 配置](#4-mcp-skill-配置)
5. [高级功能](#5-高级功能)
6. [常见问题](#6-常见问题)
7. [合规说明](#7-合规说明)

---

## 1. 快速开始

### 1.1 安装依赖

```bash
cd zhihu_download
pip install -r requirements.txt
```

> **注意**: weasyprint 需要系统级依赖，详见 [weasyprint 安装文档](https://doc.courtbouillon.org/weasyprint/stable/first_install.html)

### 1.2 系统依赖安装

**Ubuntu/Debian:**
```bash
sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libcairo2-dev
```

**macOS:**
```bash
brew install pango harfbuzz cairo pango gdk-pixbuf
```

**Windows:**
```bash
# 使用 pip 安装即可，weasyprint 会自带依赖
pip install weasyprint
```

### 1.3 获取 Cookie

Cookie 是访问知乎账号的凭证，获取步骤如下：

使用Cookie Editor浏览器插件，在知乎页面，导出为json格式

---

## 2. CLI 命令行使用

### 2.1 Cookie 授权

**方式一：交互式配置（推荐）**

```bash
python cli/main.py auth
```

按提示粘贴 Cookie 字符串，系统会自动验证并保存。

**方式二：从 JSON 文件加载**

如果有 `cookies.json` 文件：

```bash
python cli/main.py auth --json cookies.json
```

**方式三：命令行直接提供**

```bash
python cli/main.py auth "your_cookie_string_here"
```

**验证授权状态：**

```bash
python cli/main.py auth
```

如果已授权，会提示"已找到保存的 Cookie"，可选择是否重新配置。

### 2.2 列出收藏夹

```bash
python cli/main.py list
```

**输出示例：**
```
共找到 5 个收藏夹
┌──────────┬────────────────┬──────────┬─────────┐
│ ID       │ 名称           │ 创建者   │ 内容数  │
├──────────┼────────────────┼──────────┼─────────┤
│ 998150123│ 技术干货       │ 张三     │ 156     │
│ 887654321│ 学习资料       │ 李四     │ 89      │
│ 776543210│ 产品设计       │ 王五     │ 234     │
└──────────┴────────────────┴──────────┴─────────┘
```

> **注意**: 如果知乎 API 暂时不可用，系统会提示你手动输入收藏夹 ID

### 2.3 导出收藏夹

**基本用法：**

```bash
# 导出为 Markdown
python cli/main.py export 998150123 -f md

# 导出为 PDF
python cli/main.py export 998150123 -f pdf

# 同时导出多种格式
python cli/main.py export 998150123 -f md -f pdf -f html -f csv
```

**常用选项：**

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output PATH` | 输出目录 | `./downloads` |
| `-f, --format TEXT` | 导出格式（可多次） | `md` |
| `--delay-min INT` | 最小延迟（秒） | `1` |
| `--delay-max INT` | 最大延迟（秒） | `3` |
| `--resume` | 断点续传 | 否 |
| `--force` | 强制重新导出 | 否 |
| `--dedupe` | 启用内容去重 | 否 |

**输出目录结构：**

```
downloads/
└── collection_998150123/
    ├── markdown/          # Markdown 格式
    │   ├── assets/        # 图片资源（按文章标题分类）
    │   │   └── 文章标题 1/
    │   │       ├── image1.jpg
    │   │       └── image2.png
    │   ├── 文章标题 1.md
    │   └── 文章标题 2.md
    ├── pdf/               # PDF 格式
    │   ├── 文章标题 1.pdf
    │   └── 文章标题 2.pdf
    ├── html/              # HTML 单文件格式（离线浏览）
    │   ├── 文章标题 1.html
    │   └── 文章标题 2.html
    ├── csv/               # CSV 台账（元数据索引）
    │   └── collection_998150123_metadata.csv
    └── logs/              # 日志文件
```

### 2.4 打包为 ZIP

导出完成后，可将结果打包为 ZIP 文件便于分享和归档：

```bash
# 基本用法
python cli/main.py zip 998150123

# 指定包含的格式
python cli/main.py zip 998150123 -f md -f pdf

# 文件名不包含时间戳
python cli/main.py zip 998150123 --no-timestamp
```

**输出示例：**
```
打包完成！
ZIP 文件：./downloads/collection_998150123_20260314_120000.zip

文件信息：
  文件数：156
  压缩后大小：45.23 MB
  压缩率：68.5%
```

### 2.5 高级用法

**断点续传：**

导出过程中断后，继续未完成的导出：

```bash
python cli/main.py export 998150123 --resume
```

系统会自动跳过已导出的文章。

**强制重新导出：**

忽略已存在的文件，重新导出所有内容：

```bash
python cli/main.py export 998150123 --force
```

**内容去重：**

启用基于 URL 的去重，跳过已导出的内容：

```bash
python cli/main.py export 998150123 --dedupe
```

**调整请求延迟：**

```bash
# 更快（但可能增加被限流风险）
python cli/main.py export 998150123 --delay-min 0.5 --delay-max 1

# 更安全
python cli/main.py export 998150123 --delay-min 2 --delay-max 5
```

---

## 3. Web UI 使用

Web UI 提供图形化界面，适合不熟悉命令行的用户。

### 3.1 启动 Web UI

```bash
python web/server.py
```

浏览器访问：http://localhost:8000

### 3.2 界面说明

**侧边栏导航：**
- 📑 **收藏夹管理** - 添加和管理收藏夹
- 📄 **文章列表** - 查看和选择文章
- ⚙️ **导出任务** - 查看导出进度
- 🔧 **设置** - Cookie 和导出目录配置

### 3.3 使用步骤

**步骤 1：配置 Cookie**

1. 点击侧边栏 **设置**
2. 在 Cookie JSON 粘贴区域输入 cookies.json 内容
3. 点击 **保存 Cookie**
4. 状态指示器变为绿色表示成功

**步骤 2：添加收藏夹**

1. 点击 **收藏夹管理**
2. 在输入框粘贴收藏夹 URL 或 ID
   - URL 格式：`https://www.zhihu.com/collection/998150123`
   - ID 格式：`998150123`
3. 点击 **添加** 按钮
4. 系统自动解析并显示收藏夹信息

**步骤 3：选择文章**

1. 点击 **文章列表**
2. 在顶部选择要导出的收藏夹
3. 勾选要导出的文章（支持全选/取消全选/反选）
4. 底部显示已选文章数量

**步骤 4：开始导出**

1. 在底部导出栏选择导出格式
   - ☑️ Markdown
   - ☑️ PDF
   - ☐ HTML
   - ☐ CSV
2. 点击 **开始导出** 按钮
3. 切换到 **导出任务** 查看进度

### 3.4 输出目录配置

在 **设置** 页面可修改输出目录：

```
./downloads           # 相对路径（默认）
/home/user/zhihu      # 绝对路径（Linux/macOS）
D:\zhihu_exports      # 绝对路径（Windows）
```

---

## 4. MCP Skill 配置

MCP (Model Context Protocol) 允许通过自然语言调用本工具。

### 4.1 配置 MCP Server

在 Claude Code 或其他 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "zhihu-collections": {
      "command": "python",
      "args": ["/absolute/path/to/zhihu_download/mcp/server.py"]
    }
  }
}
```

### 4.2 自然语言调用示例

```
帮我列出所有知乎收藏夹

导出收藏夹 998150123 为 Markdown 格式

搜索包含"技术"的收藏夹

获取收藏夹 998150123 的文章数量
```

### 4.3 可用工具

| 工具 | 功能 |
|------|------|
| `list_collections` | 列出所有收藏夹 |
| `export_collection` | 导出指定收藏夹 |
| `get_collection_info` | 获取收藏夹信息 |
| `search_collections` | 搜索收藏夹 |

---

## 5. 高级功能

### 5.1 导出格式说明

**Markdown (.md)**
- 优点：轻量、可编辑、兼容性好
- 适用：知识管理、二次编辑
- 图片：下载到 `assets/文章标题/` 目录

**PDF (.pdf)**
- 优点：排版精美、离线阅读
- 适用：打印、归档
- 注意：需要安装 weasyprint 系统依赖

**HTML 单文件 (.html)**
- 优点：自包含、离线浏览、排版还原
- 适用：网页浏览、分享
- 特点：CSS 内联、图片可 Base64 编码

**CSV 台账 (.csv)**
- 优点：结构化数据、便于检索
- 适用：元数据管理、Excel 分析
- 字段：标题、URL、类型、作者、发布时间等

### 5.2 日志文件

日志文件保存在 `downloads/collection_<ID>/logs/` 目录：

```
logs/
└── zhihu_download_20260314_120000.log
```

日志包含：
- 每篇文章的抓取状态
- 错误详情和堆栈跟踪
- 请求延迟信息

### 5.3 版权说明

每篇导出的内容都会自动添加版权声明：

```markdown
> https://www.zhihu.com/question/xxx/answer/xxx

本内容仅供个人非商用学习备份使用，版权归知乎平台及原作者所有。
原文链接：https://www.zhihu.com/question/xxx/answer/xxx
```

---

## 6. 常见问题

### Q1: Cookie 验证失败？

**A:** Cookie 可能已过期，请重新获取并运行 `auth` 命令。

```bash
python cli/main.py auth
```

### Q2: PDF 生成报错 `OSError: [Errno 2] No such file or directory`？

**A:** weasyprint 缺少系统级依赖。

**Ubuntu/Debian:**
```bash
sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libcairo2-dev
```

**macOS:**
```bash
brew install pango harfbuzz cairo pango gdk-pixbuf
```

**Windows:** 确保使用官方安装包或 `pip install weasyprint`

### Q3: 导出速度慢？

**A:** 默认 1-3 秒延迟是为了避免被知乎限流。如确需加速：

```bash
python cli/main.py export 998150123 --delay-min 0.5 --delay-max 1
```

> ⚠️ **警告**: 过快的请求可能导致账号被暂时限流

### Q4: 图片无法下载？

**A:** 检查以下事项：
1. Cookie 是否有效（重新运行 `auth`）
2. 网络连接是否正常
3. 部分图片可能需要特定 Referer 头

### Q5: 中文 PDF 显示乱码？

**A:** 系统缺少中文字体。

**Ubuntu/Debian:**
```bash
sudo apt-get install fonts-noto fonts-wqy-zenhei
```

**macOS:** 系统自带中文字体，无需额外安装

### Q6: list 命令返回空列表？

**A:** 知乎 API 暂时不可用。请使用以下方式获取收藏夹 ID：

1. 浏览器打开知乎收藏夹页面
2. 从 URL 中复制 ID
   - 例如：`https://www.zhihu.com/collection/998150123`
   - ID 为：`998150123`
3. 直接使用 `export` 命令导出

### Q7: 如何删除已保存的 Cookie？

**A:** 运行 `auth` 命令并确认清除：

```bash
python cli/main.py auth
# 选择"是"重新配置，会自动清除旧 Cookie
```

或手动删除文件：
- Linux/macOS: `~/.zhihu_download/.cookies.encrypted`
- Windows: `C:\Users\<用户>\.zhihu_download\.cookies.encrypted`

---

## 7. 合规说明

⚠️ **重要提示**：本工具仅供**个人非商用学习备份**使用

**允许的行为：**
- ✅ 导出自己有权限访问的收藏夹
- ✅ 个人离线阅读、知识管理
- ✅ 学习研究、技术分析

**禁止的行为：**
- ❌ 不得用于商用分发
- ❌ 不得抓取付费内容全文（盐选等）
- ❌ 不得高频请求影响知乎服务
- ❌ 不得将数据上传至第三方服务器

**使用本工具即表示同意遵守：**
- 相关法律法规
- 知乎用户协议
- 数据使用道德规范

---

## 附录

### A. 快捷键参考

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+C` | 中断导出（已导出的内容不会丢失） |
| `Ctrl+Z` | 挂起进程（Linux/macOS） |

### B. 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ZHIHU_OUTPUT_DIR` | 默认输出目录 | `./downloads` |
| `ZHIHU_DEBUG` | 开启调试日志 | `0` |

### C. 文件位置

| 文件 | 位置 |
|------|------|
| Cookie 加密文件 | `~/.zhihu_download/.cookies.encrypted` |
| 盐值文件 | `~/.zhihu_download/.salt` |
| 日志文件 | `downloads/collection_<ID>/logs/` |

---

**技术支持**: 如有问题，请查看日志文件或联系项目维护者。
