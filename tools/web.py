import re
import httpx
from tools.base import Tool

try:
    from playwright.sync_api import sync_playwright
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=False)
    _page = _browser.new_page()
    _HAS_PLAYWRIGHT = True
except Exception:
    _HAS_PLAYWRIGHT = False


class WebTool(Tool):
    name = "web"
    description = (
        "网页工具，通过 action 选择模式：\n"
        "  fetch     - 快速抓取网页纯文本（参数 url）\n"
        "  navigate  - 浏览器打开 URL（参数 url）\n"
        "  click     - 点击元素（参数 selector）\n"
        "  type      - 输入文本（参数 selector + text）\n"
        "  read      - 读取当前页面纯文本\n"
        "  screenshot - 截图（参数 path，可选）"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["fetch", "navigate", "click", "type", "read", "screenshot"],
                "description": "操作模式",
            },
            "url": {"type": "string", "description": "网址"},
            "selector": {"type": "string", "description": "CSS 选择器"},
            "text": {"type": "string", "description": "要输入的文本"},
            "path": {"type": "string", "description": "截图保存路径"},
        },
        "required": ["action"],
    }

    def run(self, args: dict) -> str:
        action = args["action"]

        # ── fetch 模式：httpx 抓取 ──
        if action == "fetch":
            url = args.get("url", "")
            if not url:
                return "ERROR: fetch 需要 url 参数"
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url)
            r.raise_for_status()
            text = self._extract_text(r.text)
            return text[:30000]

        # ── 其余模式：Playwright ──
        if not _HAS_PLAYWRIGHT:
            return "ERROR: playwright 未安装。运行: pip install playwright; python -m playwright install chromium"

        global _page

        if action == "navigate":
            _page.goto(args.get("url", ""), timeout=30000)
            return f"已打开 {args.get('url')}\n页面标题: {_page.title()}\n\n可交互元素:\n{self._list_elements()}"

        elif action == "click":
            _page.click(args.get("selector", ""), timeout=10000)
            _page.wait_for_load_state("networkidle")
            return f"已点击 {args.get('selector')}"

        elif action == "type":
            _page.fill(args.get("selector", ""), args.get("text", ""), timeout=10000)
            return f"已在 {args.get('selector')} 输入: {args.get('text')}"

        elif action == "read":
            text = self._extract_text(_page.content())
            return text[:30000]

        elif action == "screenshot":
            path = args.get("path", "screenshot.png")
            _page.screenshot(path=path, full_page=True)
            return f"截图已保存到 {path}"

        return f"ERROR: 未知 action: {action}"

    @staticmethod
    def _extract_text(html: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _list_elements(self) -> str:
        """提取页面输入框和按钮，生成可用 CSS 选择器"""
        global _page
        try:
            items = _page.evaluate("""() => {
                const els = document.querySelectorAll('input:not([type=hidden]), button, select, textarea, a.btn, a[role=button]');
                return Array.from(els).slice(0, 30).map(el => {
                    const id = el.id ? '#' + el.id : '';
                    const nodename = el.nodeName.toLowerCase();
                    const name = el.name ? nodename + '[name="' + el.name + '"]' : '';
                    const cls = '.' + (el.className || '').trim().split(/\\s+/g).slice(0, 2).join('.');
                    const sel = id || name || cls || nodename;
                    const type = el.getAttribute('type') || nodename;
                    const placeholder = el.getAttribute('placeholder') || '';
                    const text = (el.textContent || el.value || '').trim().slice(0, 30);
                    return sel + '  [' + type + ']  ' + (placeholder ? 'placeholder="' + placeholder + '"  ' : '') + text;
                });
            }""")
            return "\n".join(items) if items else "(无表单元素)"
        except Exception as e:
            return f"(提取元素失败: {e})"
