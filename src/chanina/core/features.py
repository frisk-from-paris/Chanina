from typing import Callable

import celery


class ChaninaTask(celery.Task):
    """
    Base class for Tasks used by the Chanina app.
    This class is meant to be inherited by the user's implementation of specific
    base Tasks.
    """
    ...


class Feature:
    """
        The Feature object is the interface that allows users to create a function with
        access to the playwright context that can be treated as a celery Task.
    """
    def __init__(
        self,
        app,
        func: Callable,
        feature_id: str,
        **celery_kwargs
    ) -> None:
        self.app = app
        self.func = func
        self.feature_id = feature_id
        self.celery_kwargs = celery_kwargs
        
        self.task = self._register_as_task()

    def _register_as_task(self):
        """ register the feature as a celery task. """
        @self.app.celery.task(
            name=self.feature_id,
            **self.celery_kwargs
        )
        def _task(*args, **kwargs):
            args = () if None in args else ()
            return self.func(*args, self.app.worker_session, kwargs.get("args"))
        return _task
