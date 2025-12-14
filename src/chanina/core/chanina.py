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

from chanina.core.features import Feature
from chanina.core.worker_session import WorkerSession
from chanina.default_features import build_default_features

from celery import Celery, signals
from redis import Redis


def init_profile(profile_path: str):
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
        backend: str,
        broker: str,
        redis_host: str,
        redis_port: int,
        user_profile_path: str = "",
        headless: bool = False,
        browser_name: str = "firefox",
    ) -> None:
        # Inside the celery worker process the __file__ might be dir.module
        caller_path = str(Path(caller_path).resolve().parent)

        self._in_use_profile_path = None
        self.worker_session = None
        self.features = {}

        self.redis = Redis(host=redis_host, port=redis_port)
        self.redlock = f"lock:{caller_path}"
        self.celery = Celery("chanina", broker=broker, backend=backend)

        self._caller_path = caller_path
        self._headless = headless
        self._browser_name = browser_name
        self._user_profile_path = user_profile_path

        signals.worker_process_init.connect(self._init_worker)
        signals.worker_process_shutdown.connect(self._shutdown_worker)

        # After the definition of self.features and self.celery, we build the default features.
        build_default_features(self)

    def _init_worker(self, **_):
        """
        Initializes the worker_session and the profile.
        A redis lock is placed on the 'lock:self._caller_path' key so only one worker at
        a time is handling the file system.
        """
        with self.redis.lock(self.redlock,timeout=30, blocking_timeout=45):
            logging.warning("Locking to start the session ...")
            profile = self._user_profile_path
            if profile:
                self._in_use_profile_path = init_profile(profile)
            self.worker_session = WorkerSession(
                caller_path=self._caller_path,
                headless=self._headless,
                browser_name=self._browser_name,
                app=self,
                profile=profile
            )
            logging.info(f"WorkerSession initialized: {self._in_use_profile_path}")

    def _shutdown_worker(self, **_):
        """ Deleted profiles and close session at shutdown. """
        if self._in_use_profile_path:
            remove_profile(self._in_use_profile_path)
        if self.worker_session:
            self.worker_session.close()
            self.worker_session = None
        logging.info("WorkerSession closed")

    def feature(self, feature_id: str, **kwargs) -> Callable:
        """
        Decorator for feature to be added to the main
        loop.
        The new feature is registered in a dict with the given identifier
        as the "command name" that will trigger the feature.
        """
        def decorator(func: Callable) -> Callable:
            feature = Feature(
                app=self,
                func=func,
                feature_id=feature_id,
                **kwargs
            )
            self.features[feature_id] = feature 
            return func
        return decorator
