""" tools for navigating a page.
functions do not return anything but make the current_page to the desired state.
"""
from typing import Literal

import logging

from chanina.tools._meta_tools import normalize_url


class Navigate:
    def __init__(self, session) -> None:
        self.session = session

    def goto(
        self,
        url: str,
        timeout: int = 15000,
        allow_redirect: bool = True,
        wait_event: Literal[
            "load",
            "domcontentloaded",
            "networkidle"
        ] = "networkidle"
    ) -> None:
        """
        Go to the desired url and assure the page is fully loaded in a timely manner.
    
        Args:
            - url (str): url to go to.
            - timeout (float): max timeout to wait for the page to load (ms).
            - allow_redirect (bool): If set to False, raise Exception if page is redirected.
            - wait_event (Literal[str]): event to wait until.
        """
        url = normalize_url(url)
        response = self.session.get_current_page().goto(url, timeout=timeout, wait_until=wait_event)
        self.session.get_current_page().wait_for_load_state(wait_event)
        if not response:
            raise Exception(f"did not get response from {url}.")
        #if not response.status in range(200, 299):
        #    raise Exception(f"got status code : {response.status}.")
        if not allow_redirect and not response.url == url:
            raise Exception(f"unauthorized rediction to {response.url}.")
    
    
    def scroller(
        self,
        scroller_depth: int = 0,
        axis: Literal['y', 'x'] = 'y',
        timeout: int = 2000,
        speed: int = 50,
        max_scrolls: int = 0
    ) -> None:
        """
        scroll all the way down a scroll bar.
    
        Args:
            - scroller_depth (int): which depth should the scrollbar be at, 0 being the full doc, 1 the first
                                    scrollable container inside the full doc, 2 the second ... etc.
            - axis (Literal['y', 'x']): scrolling axis.
            - timeout (int): for dynamically generated content.
                             If a value is set, waits 'reload_timeout' ms and check if scroll_bar is still maxed.
        """
        page = self.session.current_page

        scrollables = page.query_selector_all("*")
        handles = []
        for el in scrollables:
            is_scrollable = el.evaluate(
                """el => {
                    const style = getComputedStyle(el);
                    return (
                        ((el.scrollHeight - el.clientHeight > 5) || (el.scrollWidth - el.clientWidth > 5)) &&
                        /(auto|scroll)/.test(style.overflow + style.overflowX + style.overflowY)
                    );
                }"""
            )
            if is_scrollable:
                handles.append(el)
        try:
            el = handles[scroller_depth]
        except IndexError:
            el = handles[0]

        def get_scroll_pos():
            return page.evaluate(f"(el) => el.{axis_scroll}", el)
    
        def get_scroll_size():
            return page.evaluate(f"(el) => el.{axis_size}", el)
    
        def get_client_size():
            return page.evaluate(f"(el) => el.{axis_client}", el)
    
        axis_scroll = "scrollTop" if axis == "y" else "scrollLeft"
        axis_size = "scrollHeight" if axis == "y" else "scrollWidth"
        axis_client = "clientHeight" if axis == "y" else "clientWidth"
        previous_pos = get_scroll_pos()
        client_size = get_client_size()
        scroll_size = get_scroll_size()
    
        if scroll_size <= client_size:
            logging.warning(f"'{el}' does not have a scroll bar.")
    
        scrolls_count = 1
        condition = lambda c: c <= max_scrolls if max_scrolls else True

        while condition(scrolls_count):
            page.evaluate(f"(el) => el.{axis_scroll} += {speed}", el)
            current_pos = get_scroll_pos()
            if current_pos == previous_pos:
                page.wait_for_timeout(timeout)
                page.evaluate(f"(el) => el.{axis_scroll} += 50", el)
                current_pos = get_scroll_pos()
                if current_pos == previous_pos:
                    break
            previous_pos = current_pos
            scrolls_count += 1
