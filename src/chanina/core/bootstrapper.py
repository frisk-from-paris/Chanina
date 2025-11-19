import logging
from chanina.core.chanina import Feature

from celery import chain, group


class Sequencer:
    """ The sequencer is maintaining the current sequence being bootstrapped. """
    def __init__(self) -> None:
        self.registry = {}
        self._sequence = None
        self.tasks_by_flow_id = {"default.chain": [], "default.group": []}

    @property
    def sequence(self):
        return self._sequence

    def add(self, step: dict, feature: Feature, args: dict = {}):
        """
        To add the step to the sequence, we need to check its content: 
            - identifier needs to be unique
            - flow_type needs to be group or chain
            - flow_id if unspecified will be default.{flow_type}, else it will be on its own key in the register.
        Steps are added in the order they are written in the yaml file, depending on their own flow_id.
        """
        args = args
        name = step["identifier"]
        flow_type = step["flow_type"]
        if not flow_type in ["chain", "group"]:
            raise ValueError(f"'{flow_type}' is not a valid flow_type.")

        flow_id = step.get("flow_id", None)
        flow_id = f"{flow_id}.{flow_type}" if flow_id else f"default.{flow_type}"

        task = feature.task.s(args=args)
        self.tasks_by_flow_id.setdefault(flow_id, [])
        self.tasks_by_flow_id[flow_id].append(task)
        self.registry[name] = task

    def build(self):
        """
        Builds the sequence.
        """
        sequence = []
        for flow, tasks in self.tasks_by_flow_id.items():
            if flow.split(".")[1] == "group":
                sequence.append(group(tasks))
            elif flow.split(".")[1] == "chain":
                sequence.append(chain(tasks))
        self._sequence = sequence


class Bootstrapper:
    """
    The Bootstrapping is the process where the workflow and features are turned into a sequence 
    of celery 'chains' or 'groups' that can be ran by the Runner.
    """
    def __init__(self, features: dict[str, Feature], workflow: dict) -> None:
        self.features = features
        self.workflow = workflow
        self._sequencer = Sequencer()
        self._built = False
    
    @property
    def built(self):
        return self._built

    @property
    def sequencer(self):
        return self._sequencer

    @property
    def sequence(self):
        if not self.built:
            logging.error(f"Trying to access sequence before the bootstrapper has been built.")
            return []
        return self._sequencer.sequence

    def build(self):
        """
        The build process is creating a sequence of chains and groups.
        When a step is a 'chain' 'flow_type', it is added to a chain list.
        Whenever another a step has another 'flow_type', the chain list is appended
        to the sequence, and a new list is created to append the other 'flow_type',
        etc.
        """
        if self.built:
            raise Exception("You cannot build a Bootstrapper more than once.")

        for step in self.workflow["steps"]:
            feature = self.features.get(step["identifier"])
            if not feature:
                logging.error(f"{step['identifier']} is not implemented.")
                continue
            # If the step needs multiple instances we build it here.
            if step["identifier"] in self.workflow["instances"].keys():
                initial_args = step.get("args", {}) or {}
                for args in self.workflow["instances"][step["identifier"]]:
                    # 'instances' are dicts of args with which we re-run the task.
                    args.update(initial_args)
                    self.sequencer.add(step, feature, args)
            # Otherwise we build the task here.
            else:
                # 'step' is passed as 'args' cause it does contain the args at the key 'args'.
                all_args = step.get("args", {})
                self.sequencer.add(step, feature, all_args)
        self.sequencer.build()
        self._built = True
