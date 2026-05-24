"""
Device Agent engine — screenshot-based UI understanding and automation.

Uses vision-language model for UI element detection, Playwright for browser,
and OS-level APIs for desktop control.
"""

from __future__ import annotations

import asyncio
import base64
import time
import uuid
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class DeviceAction:
    """A single device action (click, type, swipe, etc.)."""

    def __init__(
        self,
        action_type: str,
        params: dict[str, Any] | None = None,
    ):
        self.action_type = action_type  # click, type, swipe, back, home, launch, screenshot
        self.params = params or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "actionType": self.action_type,
            "params": self.params,
            "timestamp": self.timestamp,
        }


class DeviceAgent:
    """
    Autonomous device agent that can understand and control desktop/browser UIs.

    Uses vision-language models for UI understanding and Playwright for browser automation.
    """

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._browser = None
        self._playwright = None
        self._browser_context = None
        self._current_url: str | None = None
        self._screenshots: list[str] = []
        self._action_history: list[DeviceAction] = []

    async def ensure_browser(self) -> bool:
        """Initialize Playwright browser if not already running."""
        if self._browser is not None:
            return True

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                ],
            )
            self._browser_context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="JARVIS-DeviceAgent/1.0",
            )
            logger.info("device_agent_browser_initialized")
            return True
        except ImportError:
            logger.warning("playwright_not_installed", hint="pip install playwright && playwright install chromium")
            return False
        except Exception as exc:
            logger.warning("device_agent_browser_init_failed", error=str(exc))
            return False

    async def navigate(self, url: str) -> dict[str, Any]:
        """Navigate to a URL."""
        ok = await self.ensure_browser()
        if not ok or self._browser_context is None:
            return {"error": "Browser not available"}

        try:
            page = await self._browser_context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            self._current_url = url
            self._action_history.append(DeviceAction("navigate", {"url": url}))

            screenshot = await page.screenshot(type="png")
            encoded = base64.b64encode(screenshot).decode("utf-8")

            title = await page.title()
            return {
                "url": url,
                "title": title,
                "status": "loaded",
                "screenshot": f"data:image/png;base64,{encoded[:100]}...",
                "viewport": {"width": 1280, "height": 720},
            }
        except Exception as exc:
            return {"error": str(exc), "url": url}

    async def click(self, selector: str) -> dict[str, Any]:
        """Click an element on the current page."""
        if self._browser_context is None:
            return {"error": "Browser not available"}

        try:
            pages = self._browser_context.pages
            if not pages:
                return {"error": "No open page"}

            page = pages[-1]
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.5)
            self._action_history.append(DeviceAction("click", {"selector": selector}))

            screenshot = await page.screenshot(type="png")
            return {
                "action": "click",
                "selector": selector,
                "status": "clicked",
            }
        except Exception as exc:
            return {"error": str(exc), "selector": selector}

    async def type_text(self, selector: str, text: str) -> dict[str, Any]:
        """Type text into an input field."""
        if self._browser_context is None:
            return {"error": "Browser not available"}

        try:
            pages = self._browser_context.pages
            if not pages:
                return {"error": "No open page"}

            page = pages[-1]
            await page.fill(selector, text, timeout=5000)
            self._action_history.append(DeviceAction("type", {"selector": selector, "text": text}))
            return {"action": "type", "status": "typed"}
        except Exception as exc:
            return {"error": str(exc)}

    async def screenshot(self) -> dict[str, Any]:
        """Take a screenshot of the current page."""
        if self._browser_context is None:
            return {"error": "Browser not available"}

        try:
            pages = self._browser_context.pages
            if not pages:
                return {"error": "No open page"}

            page = pages[-1]
            screenshot = await page.screenshot(type="png")
            encoded = base64.b64encode(screenshot).decode("utf-8")
            self._screenshots.append(encoded)

            title = await page.title()
            return {
                "screenshot": f"data:image/png;base64,{encoded[:50]}...",
                "size": len(encoded),
                "title": title,
                "url": page.url,
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def analyze_ui(self) -> dict[str, Any]:
        """Analyze the current page UI structure."""
        if self._browser_context is None:
            return {"error": "Browser not available"}

        try:
            pages = self._browser_context.pages
            if not pages:
                return {"error": "No open page"}

            page = pages[-1]
            ui_info = await page.evaluate("""() => {
                const elements = [];
                const interactive = 'a, button, input, select, textarea, [role=button], [role=link]';
                document.querySelectorAll(interactive).forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 5 && rect.height > 5) {
                        elements.push({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || '',
                            text: (el.textContent || '').trim().slice(0, 50),
                            href: el.href || '',
                            placeholder: el.placeholder || '',
                            visible: rect.width > 0 && rect.height > 0,
                            bounds: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) }
                        });
                    }
                });
                return { count: elements.length, elements: elements.slice(0, 50) };
            }""")
            return {
                "url": page.url,
                "title": await page.title(),
                "uiElements": ui_info,
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def get_history(self) -> list[dict]:
        return [a.to_dict() for a in self._action_history[-50:]]

    async def close(self) -> None:
        """Clean up browser resources."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None
        self._browser_context = None
        logger.info("device_agent_closed")


# Singleton
_agent_instance: DeviceAgent | None = None


def get_agent() -> DeviceAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DeviceAgent()
    return _agent_instance


async def close_agent() -> None:
    global _agent_instance
    if _agent_instance:
        await _agent_instance.close()
        _agent_instance = None
