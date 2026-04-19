[English](README.md)

# drission-kernel

[![CI](https://github.com/cancelpt/drission-kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/cancelpt/drission-kernel/actions/workflows/ci.yml)

`drission-kernel` 是一个构建在 DrissionPage 之上的可复用浏览器自动化包。它聚焦于 Chromium 会话启动、命名标签页复用、通用等待辅助以及反爬辅助原语，适合作为更高层自动化项目的浏览器内核。

## 它提供什么

- 通过 `BrowserBootstrapConfig` 和 `create_browser_session()` 启动浏览器会话
- 通过 `BrowserSession.get_tab(site_name)` 复用命名标签页
- 在调用 `close_tab()` 或 `quit()` 后自动失效的生命周期安全标签页句柄
- 会话级别的 cookie 和 local storage 辅助方法
- `wait_for_element()`、`wait_for_title()`、`url_contains()` 等通用等待辅助
- `drission_kernel.anti_bot` 中面向 SafeLine 和 Cloudflare 挑战页的反爬辅助函数

## 适用场景

- 作为更高层自动化流程的共享浏览器会话基础设施
- 在稳定的 DrissionPage 会话抽象之上承载业务逻辑的项目
- 需要命名标签页、cookie 与 local storage 辅助能力、以及可复用反爬原语的工作负载
- 希望把流程编排、解析逻辑和领域规则放在上层的团队

## 安装

环境要求：

- Python 3.11+
- DrissionPage 可访问到的 Chrome 或 Chromium 浏览器

在仓库根目录安装：

```bash
pip install .
```

如果 DrissionPage 不能自动识别浏览器路径，可以在 `BrowserBootstrapConfig` 中显式设置 `browser_path`。

## 快速开始

```python
from drission_kernel import (
    BrowserBootstrapConfig,
    create_browser_session,
    url_contains,
    wait_for_element,
)

config = BrowserBootstrapConfig(
    browser_path="/path/to/chrome",  # 如果 DrissionPage 能自动识别，可省略
    download_path="/tmp/drission-kernel/downloads",
    user_data_dir="/tmp/drission-kernel/profile",
    language="en-US",
)

session = create_browser_session(headless=True, config=config)

try:
    tab = session.get_tab("example")
    tab.get("https://example.com", timeout=10)

    if url_contains(tab, "example.com", timeout=5):
        heading = wait_for_element(tab, "tag:h1", timeout=10)
        print(heading.text)

    session.set_local_storage("example", {"mode": "demo"})
    print(session.get_local_storage("example"))
    print(session.get_cookies())
finally:
    session.quit()
```

命名标签页会按逻辑名称复用。只要标签页未被关闭、会话未结束，再次调用 `session.get_tab("example")` 会返回同一个句柄。

## API 概览

### 会话启动

- `BrowserBootstrapConfig`：配置 user agent、代理、下载目录、用户数据目录、浏览器路径和浏览器语言
- `create_browser_session(browser=None, headless=False, config=None)`：基于新建 Chromium 浏览器或注入的浏览器实现创建 `DrissionBrowserSession`

### 会话操作

- `get_tab(site_name)`：返回稳定的命名标签页句柄
- `close_tab(site_name)`：关闭一个命名标签页，并使此前发出的同名句柄失效
- `set_cookies(cookies)` / `get_cookies(target_domain=None)`：写入和查询 cookie
- `set_local_storage(site_name, payload)` / `get_local_storage(site_name)`：针对命名标签页上下文读写 local storage
- `quit()`：关闭整个浏览器会话，并使所有仍在持有的标签页句柄失效

### 标签页与监听器操作

- 标签页句柄支持 `get()`、`ele()`、`eles()`、`refresh()` 和 `run_js()`
- 标签页句柄也暴露 `url`、`title`、`html` 和 `raw`，便于访问底层页面状态
- `tab.listen.start(...)`、`tab.listen.wait(...)` 和 `tab.listen.stop()` 提供受控的网络监听能力

### 等待辅助

- `wait_for_element(tab, selector, timeout=10, index=1)`
- `wait_for_title(tab, expected_title, timeout=10)`
- `url_contains(tab, expected_url, timeout=0.2)`

### 反爬辅助

从 `drission_kernel.anti_bot` 导入以下函数：

- `auto_bypass(page)`
- `bypass_ctlc(page)`，用于 SafeLine / 雷池流程
- `bypass_cloudflare(page)`
- `bypass_cloudflare_component(page, ...)`
- `random_click(page, x, y)`

### 协议契约

- `BrowserSession`、`TabHandle` 和 `ListenerHandle` 可用于类型检查，或适配其他浏览器实现

## 开发与验证

以可编辑模式安装并带上测试与 lint 依赖：

```bash
pip install -e .[test,lint]
```

安装本地 commit hook：

```bash
pre-commit install
```

在整个仓库范围内手动运行 hook 检查：

```bash
pre-commit run --all-files
```

运行测试：

```bash
pytest -q
```

运行基于 Docker 的包验证：

```bash
docker build -t drission-kernel:test .
docker run --rm drission-kernel:test
```

这个容器会在 `python:3.11-slim` 之上安装 Chromium，先执行一次基于本地页面的无头浏览器 smoke check，再运行 `pytest -q`。

## 许可

本仓库源码采用 MIT License 发布，完整文本见 `LICENSE`。

当前运行时依赖窗口为 `DrissionPage~=4.0.4.21`。这个范围内的 `4.0.4.25` PyPI 分发包声明为 BSD 条款，并随包提供 BSD 3-Clause 许可文件，因此与本仓库采用 MIT 发布并不冲突。

如果以后要放宽这个依赖范围，发布前请重新核对上游许可状态。

开发工具链里还包含 `pylint`，它是 GPL-2.0-or-later；在本项目中它只作为本地与 CI 的 lint 工具使用，不属于发布包的运行时依赖。
