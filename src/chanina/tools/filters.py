import re

from playwright.sync_api import Locator


class Filters:
    """
    Filters are meant to be 'low level'.
    If you need an advanced and quick way to search for an item, use the 'find_*'
    methods, which are designed to raise Exceptions and ensure a return.
    """
    def __init__(self, session) -> None:
        self.session = session

    def filter_by_text(
        self,
        locators: list[Locator],
        text: str,
        strict: bool = False
    ) -> list[Locator] | list[None]:
        """ Filters a list of Locators by a string on their text_content. """
        if strict:
            return [loc for loc in locators if text == str(loc.text_content())]
        return [loc for loc in locators if text in str(loc.text_content())]

    def filter_by_regex(
        self,
        locators: list[Locator],
        pattern: str
    ) -> list[Locator] | list[None]:
        """ Filters a list of Locators by a regex on their text_content. """
        regex = re.compile(pattern)
        return [loc for loc in locators if regex.search(str(loc.text_content()))]
    
    def filter_not_empty(self, locators: list[Locator]) -> list[Locator]:
        """ Only keeps the locators which have non-empty content_text. """
        return [loc for loc in locators if str(loc.text_content()).strip()]
    
    def filter_by_attr(
        self,
        locators: list[Locator],
        attr: str,
        value: str,
        strict: bool = False
    ) -> list[Locator] | list[None]:
        """
        Only keeps locators for which the attribute 'attr' either contains or is the value 'value'.
        """
        if strict:
            return [loc for loc in locators if str(loc.get_attribute(attr)) == value]
        return [loc for loc in locators if value.lower() in str(loc.get_attribute(attr)).lower()]
    
    def find_one_by_attr(self, selector: str, attr: str, text_content: str) -> Locator:
        """
        Finds the first element associated to the passed selector that has the 'text_content'
        in its 'attr' attribute.
        To search for any selector type, you can set 'selector' to "*".
        """
        selectors = self.session.inspect.get_by_selector(
            selector=selector,
            n_min=1
        )
    
        filtered = self.session.filters.filter_by_attr(
            locators=selectors,
            attr=attr,
            value=text_content
        )
    
        found = None
    
        if filtered:
            found = filtered[0]
        return found

    def find_all_by_attr(self, selector: str, attr: str, text_content: str) -> list[Locator]:
        """
        Finds all locators associated to the passed selector that has the 'text_content'
        in its 'attr' attribute.
        To search for any selector type, you can set 'selector' to "*".
        """
        selectors = self.session.inspect.get_by_selector(
            selector=selector,
            n_min=1
        )
    
        filtered = self.session.filters.filter_by_attr(
            locators=selectors,
            attr=attr,
            value=text_content
        )
    
        return filtered
