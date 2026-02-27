""" 
These are default features which have internal purposes and are built at the instanciation
of the ChaninaApplication object.
"""
import logging
from chanina.core.worker_session import WorkerSession


def chanina_new_page(session: WorkerSession, _):
    """
    Open a new_page on the current session. This changes the 'current_page'
    of the session for any other tasks that will be ran after.
    """
    try:
        session.new_page()
    except Exception as e:
        logging.error(f"[ChaninaDefaultFeature] Failed to open a new page : {e}")

def chanina_list_libretti(session: WorkerSession, _):
    """
    print a dictionnary of the features.
    """
    logging.info(f"[ChaninaDefaultFeature] chanina.list_features: {session.app.features}")


def build_default_libretti(app):
    """
    There are generic useful features that can be implemented, it must
    be implemented here, and the app needs to be the user's app instance.

    The prefix 'chanina.*' is a reserved string for identifiers of internal
    tasks.
    """
    app.libretto("chanina.list_libretti")(chanina_list_libretti)
    app.libretto("chanina.new_page")(chanina_new_page)
