import re
import httpx
from tools.base import Tool

# ── 只读：抓取网页文本 ──

class WebFetch(Tool):
    name = "web_fetch"
    description = "访问网页获取纯文本内容，只读不操作"
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "网页 URL"},
        },
        "required": ["url"],
    }

    def run(self, args: dict) -> str:
        url = args["url"]
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            r = client.get(url)
        r.raise_for_status()
        text = re.sub(r"<script[^>]*>.*?</script>", "", r.text, flags=re.DOTALL | re.I)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:30000]


# ── 交互操作：浏览器自动化 ──

try:
    from playwright.sync_api import sync_playwright
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=True)
    _page = _browser.new_page()
    _HAS_PLAYWRIGHT = True
except Exception:
    _HAS_PLAYWRIGHT = False


class WebDo(Tool):
    """
    操作网页：导航、点击、输入、读取页面内容。
    依赖：pip install playwright && playwright install chromium
    """
    name = "web_do"
    description = (
        "操作浏览器网页，支持的动作(action):\n"
        "  navigate - 打开 URL，参数 url\n"
        "  click    - 点击元素，参数 selector (CSS选择器，如 '#login', 'button.submit')\n"
        "  type     - 在输入框填内容，参数 selector + text\n"
        "  read     - 读取当前页面纯文本\n"
        "  screenshot - 截屏(返回文件路径)，参数 path(可选)"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "type", "read", "screenshot"],
                "description": "要执行的动作",
            },
            "url": {"type": "string", "description": "[navigate] 目标网址"},
            "selector": {"type": "string", "description": "[click/type] CSS 选择器"},
            "text": {"type": "string", "description": "[type] 要输入的文本"},
            "path": {"type": "string", "description": "[screenshot] 截图保存路径，默认 screenshot.png"},
        },
        "required": ["action"],
    }

    def run(self, args: dict) -> str:
        if not _HAS_PLAYWRIGHT:
            return "ERROR: playwright 未安装。运行: pip install playwright && playwright install chromium"

        global _page
        action = args["action"]

        if action == "navigate":
            _page.goto(args["url"], timeout=30000)
            return f"已打开 {args['url']}\n页面标题: {_page.title()}"

        elif action == "click":
            _page.click(args["selector"], timeout=10000)
            _page.wait_for_load_state("networkidle")
            return f"已点击 {args['selector']}"

        elif action == "type":
            _page.fill(args["selector"], args["text"], timeout=10000)
            return f"已在 {args['selector']} 输入: {args['text']}"

        elif action == "read":
            html = _page.content()
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
            text = re.sub(r"<[^>]+>", "\n", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text[:30000]

        elif action == "screenshot":
            path = args.get("path", "screenshot.png")
            _page.screenshot(path=path, full_page=True)
            return f"截图已保存到 {path}"

        return f"ERROR: 未知动作 {action}"
