import os
import logging

from playwright.sync_api import Page, Playwright, sync_playwright


class WorkerSession:
    """
        The 'WorkerSession' object is a shared IN MEMORY object between every tasks inside a
        same worker. This means that this object is not serialized, but lives in memory in the
        same space as every other tasks and processes inside the current worker.

        We start a playwright session here, which will live as long as this WorkerSession
        lives.
    """
    def __init__(
        self,
        caller_path: str,
        headless: bool,
        browser_name: str,
        app,
        profile: str = ""
    ) -> None:
        # Starting playwright process ...
        logging.info(f"Running playwright from dir : '{caller_path}'")
        self._pw = sync_playwright().start()

        self._browser_name = browser_name
        self._profile = profile
        self._headless = headless
        self._profile_path = os.path.abspath(profile)

        self.app = app

        self._init_context()

        # Local context to use inside a task.
        self.user_context = {}

        logging.info("Initialized")

    @property
    def playwright(self) -> Playwright:
        """ Return playwright context. """
        return self._pw

    def _init_context(self) -> None:
        """
        Function to initialize the browser_context.
        Depending on the profile and browser_name.
        """
        if self._browser_name == "firefox":
            if self._profile:
                logging.info(f"Launching firefox with persistent context. (profile: '{self._profile_path}')")
                self.browser_context = self._pw.firefox.launch_persistent_context(
                    user_data_dir=self._profile_path,
                    headless=self._headless
                )
            else:
                logging.info("Launching firefox.")
                self.browser_context = self._pw.firefox.launch(headless=self._headless).new_context()
        elif self._browser_name == "chrome":
            logging.info("Launching Chrome")
            self.browser_context = self._pw.chromium.launch(headless=self._headless).new_context()
        else:
            raise ValueError("Browser must be 'firefox' or 'chrome'")

    def new_page(self, args: dict = {}) -> Page:
        """ Create a new page, overrides the '_current_page'. """
        return self.browser_context.new_page(**args)

    def close(self) -> None:
        """ Close the context. """
        try:
            self.browser_context.close()
        except Exception as e:
            logging.error(f"Closed with an exception : {e}")
        self._pw.stop()
        logging.warning("Stopped.")
