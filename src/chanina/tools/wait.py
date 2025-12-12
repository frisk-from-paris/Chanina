import time

from chanina.core.errors import BrowsingTimeoutException


class Wait:
    def __init__(self, session) -> None:
        self.session = session

    def wait_for_cookies(
        self,
        value: str,
        key: str = "name",
        timeout: int = 10_000
    ) -> None | bool:
        """ Wait for a cookie to be added to the browser. """
        start = time.time()
        while (time.time() - start) * 1000 < timeout:
            cookies = self.session.browser_context.cookies()
            if any(c.get(key) == value for c in cookies):
                return True
            self.session.current_page.wait_for_timeout(100)
        raise BrowsingTimeoutException("Timed out waiting for cookies.")

    def wait_for_dom_element(
        self,
        selector: str,
        timeout: int = 10_000
    ) -> None | bool:
        """Wait for a DOM element to appear."""
        start = time.time()
        page = self.session.get_current_page()
        while (time.time() - start) * 1000 < timeout:
            if page.query_selector(selector):
                return True
            page.wait_for_timeout(100)
        raise BrowsingTimeoutException(f"Timed out waiting for element '{selector}'.")

    def wait_for_js_condition(
        self,
        script: str,
        timeout: int = 10_000
    ) -> None | bool:
        """Wait for a JS condition to become true."""
        start = time.time()
        page = self.session.get_current_page()
        while (time.time() - start) * 1000 < timeout:
            if page.evaluate(script):
                return True
            page.wait_for_timeout(100)
        raise BrowsingTimeoutException(f"Timed out waiting for JS condition: {script}")
