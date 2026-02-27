"""
Operations that requires a specific state of the file system needs
to be made at the time of the ChaninaApplication initialization.
It's the only time when the program is ran, and we know for sure is not ran
in a worker but on the host system.
"""
import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import Callable

from celery import Celery, signals
from redis import Redis

from chanina.core.libretti import Libretto
from chanina.core.worker_session import WorkerSession
from chanina.default_libretti import build_default_libretti


def init_profile(profile_path: str) -> str:
    """
    A browser user profile can only be used by 1 process at the time.
    It's easier for the user not to bother with that, and let the ChaninaApplication
    handles the copying / removing on the desired profile to be used, as so the use
    of it becomes agnostic to the number of workers.
    """
    src = Path(profile_path).resolve()
    if not src.exists():
        logging.warning(f"{src} doesn't exist, defaulting to creating a persistent one.")
        os.mkdir(src)
        return str(src)
    if not src.is_dir():
        raise ValueError(f"{src} is not a valid directory.")

    dest = "tmp:" + str(uuid.uuid4())

    try:
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.lock", "lock"))
    except shutil.Error as e:
        logging.error(f"{src} could not be copied to be used as a browser profile.")
        logging.error(str(e))
        remove_profile(dest)
        return ""
    return str(dest)


def remove_profile(profile_path: str):
    """ Remove the profile used for the session. """
    p = Path(profile_path).resolve()
    if not p.is_dir():
        raise ValueError(f"{p} is not a valid directory.")
    if not "tmp:" in str(p):
        logging.info(f"{p} is a newly created persistent profile, bypassing the deletion.")
        return
    logging.info(f"Deleting temporary profile {p} ...")
    shutil.rmtree(p, ignore_errors=True)


class ChaninaApplication:
    """ Chanina application object. """
    def __init__(
        self,
        caller_path: str,
        backend: str = "redis://localhost:6379",
        broker: str = "amqp://localhost:5672",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        playwright_enabled: bool = True,
        user_profile_path: str = ".",
        headless: bool = True,
        browser_name: str = "firefox",
        celery_config: dict = {}
    ) -> None:
        # Inside the celery worker process the __file__ might be dir.module
        caller_path = str(Path(caller_path).resolve().parent)

        self.redis = Redis(host=redis_host, port=redis_port)
        self.redlock = f"lock:chanina:{caller_path}"
        self.celery = Celery("chanina", broker=broker, backend=backend)
        self.celery.config_from_object(celery_config)

        self._in_use_profile_path = ""
        self._worker_session = None
        self._libretti = {}
        self._caller_path = caller_path
        self._headless = headless
        self._browser_name = browser_name
        self._user_profile_path = user_profile_path
        self._playwright_enabled = playwright_enabled

        if playwright_enabled:
            signals.worker_process_init.connect(self._init_worker)
            signals.worker_process_shutdown.connect(self._shutdown_worker)

        # After the definition of self.features and self.celery, we build the default features.
        build_default_libretti(self)

    @property
    def libretti(self):
        return self._libretti

    @property
    def worker_session(self):
        return self._worker_session

    @property
    def playwright_enabled(self):
        return self._playwright_enabled

    def _init_worker(self, **_):
        """
        Initializes the worker_session and the profile.
        A redis lock is placed on the 'lock:self._caller_path' key so only one worker at
        a time is handling the file system.
        """
        with self.redis.lock(self.redlock,timeout=30, blocking_timeout=45):
            logging.info("Locking to start the session ...")
            if self._user_profile_path:
                self._in_use_profile_path = init_profile(self._user_profile_path)
            self._worker_session = WorkerSession(
                caller_path=self._caller_path,
                headless=self._headless,
                browser_name=self._browser_name,
                app=self,
                profile=self._in_use_profile_path
            )
            logging.info(f"WorkerSession initialized: {self._in_use_profile_path}")

    def _shutdown_worker(self, **_):
        """ Deleted profiles and close session at shutdown. """
        if self._in_use_profile_path:
            remove_profile(self._in_use_profile_path)
        if self._worker_session:
            self._worker_session.close()
            self._worker_session = None
        logging.info("WorkerSession closed")

    def libretto(self, title: str, **kwargs) -> Callable:
        """
        Decorator for feature to be added to the main
        loop.
        The new feature is registered in a dict with the given identifier
        as the "command name" that will trigger the feature.
        """
        def decorator(func: Callable) -> Callable:
            libretto = Libretto(
                app=self,
                func=func,
                title=title,
                **kwargs
            )
            self.libretti[title] = libretto
            return func
        return decorator
