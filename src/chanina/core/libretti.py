from typing import Callable


class Libretto:
    """
        The Libretto object is the interface that allows users to create a function with
        access to the playwright context that can be treated as a celery Task.
    """
    def __init__(
        self,
        app,
        func: Callable,
        title: str,
        **celery_kwargs
    ) -> None:
        self.app = app
        self.func = func
        self.title = title
        self.celery_kwargs = celery_kwargs 
        self.task = self._register_as_task()

    def _register_as_task(self):
        """ register the libretto as a celery task. """
        @self.app.celery.task(
            name=self.title,
            **self.celery_kwargs
        )
        def _task(*args, **kwargs):
            parsed_args = []
            for arg in args:
                if arg:
                    parsed_args.append(arg)
            args = tuple(parsed_args)
            if self.app.playwright_enabled:
                if args:
                    return self.func(*args, self.app.worker_session, kwargs)
                else:
                    return self.func(self.app.worker_session, kwargs)
            else:
                if args:
                    return self.func(*args, kwargs)
                else:
                    return self.func(kwargs)
        return _task
