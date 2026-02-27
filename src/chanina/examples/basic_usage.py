from chanina import ChaninaApplication


basic_app = ChaninaApplication(__file__)
playwright_disabled_app = ChaninaApplication(__file__, playwright_enabled=False)
