""" This module is allowed to catch the exceptions raised by from the third parties libraries used by Chanina. """

from playwright.sync_api import Error, WebError, TimeoutError


class BrowsingTimeoutException(TimeoutError):
    """ This exception will be raised if a timeout set by a browsing function is reached. """


class WebBrowsingException(WebError):
    """ This exception is the base of every exceptions from the web driver. """


class BrowsingException(Error):
    """ This exception is the base of every browsing exception. """
