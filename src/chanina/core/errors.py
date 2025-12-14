""" This module is allowed to catch the exceptions raised by from the third parties libraries used by Chanina. """

from playwright.sync_api import Error as BrowsingException, WebError as WebBrowsingException, TimeoutError as BrowsingTimeoutException

