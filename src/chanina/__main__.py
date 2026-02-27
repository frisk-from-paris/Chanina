import logging
from argparse import ArgumentParser

from uvicorn.importer import import_from_string, ImportFromStringError

from chanina.core.chanina import ChaninaApplication


def import_application_object(path: str) -> ChaninaApplication:
    try:
        chanina_app = import_from_string(path)
    except ImportFromStringError as e:
        logging.error(f"The specified app path is incorrect: {e}")
        raise e

    if not isinstance(chanina_app, ChaninaApplication):
        raise TypeError(
            f"{chanina_app} is not a valid ChaninaApplication object. ({type(chanina_app)})"
        )
    return chanina_app


def import_config(config: list[str]):
    """
    Parse the list of nargs passed to the cli and makes it a dict of args.
    nargs needs to be passed in the format: -r key=value key2=value2.
    Exceptions are raised if anything is not correct.
    """
    conf = {}
    if not config:
        return conf

    for kv in config:
        if not "=" in kv:
            continue
        k, v = kv.split("=")
        if not k or not v:
            raise ValueError(f"Arguments passed for flag '-r' but could not be turned into a valid dict. ({kv})")
        conf[k] = v

    if not conf:
        raise KeyError("Arguments passed for flag '-r' got parsed into an empty dictionnary.")

    return conf


def add_arguments(argparser: ArgumentParser):
    group = argparser.add_mutually_exclusive_group(required=False)
    argparser.add_argument(
        "--app",
        "-a",
        help="Path of the ChaninaApplication's instance. (format: 'module.module:app')",
        required=True,
        type=str
    )
    group.add_argument(
        "--libretto",
        "-l",
        help="Only runs the libretto specified here. (identifier only)",
        required=False,
        default="chanina.list_libretti",
        type=str
    )
    group.add_argument(
        "--celery",
        "-c",
        help="Runs the celery app, every var=value after this flag will be passed to celery.",
        required=False,
        nargs="*"
    )
    argparser.add_argument(
        "--config",
        "-g",
        help="Only in -t mode. A config to pass to the task.",
        nargs="*"
    )


def run_worker(app: ChaninaApplication, command: str = "worker", **options):
    """
    run the celery worker replacing every k=v args passed in the cli as --k=v or --k if v is bool.
    """
    argv = [command]

    for k, v in options.items():
        k = k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                argv.append(f"--{k}")
        else:
            argv.append(f"--{k}={v}")

    if app.playwright_enabled:
        argv.append("--concurrency=1")

    app.celery.start(argv)


def run():
    # Handle the arguments for the run metadatas.
    argparser = ArgumentParser()
    add_arguments(argparser)
    args = argparser.parse_args()

    app_path = args.app
    app = import_application_object(app_path)

    celery_args = args.celery
    title = args.libretto
    config_as_list = args.config

    # First we check if the command is for a celery worker.
    if isinstance(celery_args, list):
        args = import_config(celery_args)
        run_worker(app, **args)
    else:
        # Transform config into the needed components for the run.
        config = import_config(config_as_list)
        app.libretti[title].task.s(config).apply_async()

if __name__ == "__main__":
    run()
