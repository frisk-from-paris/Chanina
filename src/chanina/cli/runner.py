from argparse import ArgumentParser
import json
import os


import logging

from celery import Celery
from chanina.core.bootstrapper import Bootstrapper
from chanina.core.chanina import ChaninaApplication

import yaml
from uvicorn.importer import import_from_string, ImportFromStringError


def import_workflow_file(path: str) -> dict:
    """ This makes sure the workflow file is a valid json, and returns its content. """
    workflow = None
    if os.path.exists(path) and os.path.isfile(path):
        if path.endswith(".json"):
            try:
                with open(path, "r") as f:
                    workflow = json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding the workflow file : {e}")
                raise e
            except FileNotFoundError as e:
                logging.error(f"The workflow file does not exist : {e}")
                raise e
        elif path.endswith(".yaml") or path.endswith(".yml"):
            try:
                with open(path, "r") as f:
                    workflow = yaml.safe_load(f)
            except yaml.error.YAMLError as e:
                logging.error(f"Error decoding the workflow file : {e}")
                raise e
            except FileNotFoundError as e:
                logging.error(f"The workflow file does not exist : {e}")
                raise e
        else:
            logging.error(f"Please use an adequate file extension for your workflow.")
            raise FileExistsError("File exists but is not a correct extension")

    else:
        raise FileNotFoundError(f"'{path}' does not exist or is not a file.")
    if not workflow:
        raise ValueError("The workflow file is empty")
    return workflow 


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


def import_arguments(arguments: list[str]):
    """
    Parse the list of nargs passed to the cli and makes it a dict of args.
    nargs needs to be passed in the format: -r key=value key2=value2.
    Exceptions are raised if anything is not correct.
    """
    args = {}
    if not arguments:
        return args

    for kv in arguments:
        if not "=" in kv:
            continue
        k, v = kv.split("=")
        if not k or not v:
            raise ValueError(f"Arguments passed for flag '-r' but could not be turned into a valid dict. ({kv})")
        args[k] = v

    if not args:
        raise KeyError("Arguments passed for flag '-r' got parsed into an empty dictionnary.")

    return args


def add_arguments(argparser: ArgumentParser):
    group = argparser.add_mutually_exclusive_group(required=False)
    group.add_argument("workflow", nargs="?", type=str)
    argparser.add_argument(
        "--app",
        "-a",
        help="Path of the ChaninaApplication's instance. (format: 'module.module:app')",
        required=True,
        type=str
    )
    group.add_argument(
        "--task",
        "-t",
        help="Only runs the task specified here. (identifier only)",
        required=False,
        default=None,
        type=str
    )
    argparser.add_argument(
        "--celery",
        "-c",
        help="Runs the celery app",
        required=False,
        nargs="*"
    )
    argparser.add_argument(
        "--number_of_runs",
        "-n",
        help="How many times the task/workflow will be ran.",
        default=1,
        type=int
    )
    argparser.add_argument(
        "--arguments",
        "-r",
        help="Only in -t mode. Additionnal args to pass to the task. Warning: similar keys in the workflow will be overwritten.",
        nargs="*"
    )


class Runner:
    def __init__(
        self,
        app: ChaninaApplication,
        workflow: dict | None,
        task_identifier: str = "",
        number_of_runs: int = 1,
        additionnal_args: dict = {}
    ) -> None:
        self.app = app
        self.workflow = workflow
        self.task_identifier = task_identifier
        self.bootstrapper = Bootstrapper(
            self.app.features, workflow
        ) if workflow else None
        self.number_of_runs = number_of_runs
        self.additionnal_args = additionnal_args

        self._last_task_ids = []

    @property
    def last_task_ids(self):
        return self._last_task_ids

    def run(self):
        if self.workflow:
            self._run_workflow()
        else:
            self._run_task()

    def _run_task(self):
        feature = self.app.features[self.task_identifier]
        task = feature.task.s(args=self.additionnal_args)
        task.apply_async()

    def _run_workflow(self):
        if not self.bootstrapper:
            raise Exception("Failed to run because no Bootstrapper was initialized.")
        self.bootstrapper.build()
        if not self.bootstrapper.built or not self.bootstrapper.sequence:
            raise Exception("Can't run a sequence that the bootstrapper did not build.")

        for _ in range(self.number_of_runs):
            for sequence in self.bootstrapper.sequence:
                sequence.apply_async()


def run_celery(app: Celery,command: str = "worker", **options):
    """
    """
    argv = [command]

    for k, v in options.items():
        k = k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                argv.append(f"--{k}")
        else:
            argv.append(f"--{k}={v}")

    argv.append("--concurrency=1")
    app.start(argv)


def run():
    # Handle the arguments for the run metadatas.
    argparser = ArgumentParser()
    add_arguments(argparser)
    args = argparser.parse_args()

    app_path = args.app
    app = import_application_object(app_path)

    workflow_file = args.workflow
    celery_args = args.celery
    task_identifier = args.task
    number_of_runs = args.number_of_runs
    arguments_as_list = args.arguments

    # First we check if the command is for a celery worker.
    if isinstance(celery_args, list):
        args = import_arguments(celery_args)
        run_celery(app.celery, **args)
        return

    # Transform arguments data into the needed components for the run.
    arguments = import_arguments(arguments_as_list)
    workflow = import_workflow_file(workflow_file) if workflow_file else None

    # Create a runner
    runner = Runner(app, workflow, task_identifier, number_of_runs, arguments)
    runner.run()


if __name__ == "__main__":
    run()
