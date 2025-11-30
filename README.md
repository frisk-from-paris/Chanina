# Chanina

**Chanina** is a decorator based API that makes deploying workflows of playwright features easy and scalable.
The developper writes functions called 'features' which are injected a "WorkerSession" object that is a Playwright context.
This context is wrapped by Chanina to offer tools and functionnalities that makes implementing basic routines easier.

The workflows can be then written in YAML or JSON, and then Workers and Features are ran and orchestrated by the CLI.

This aims at transforming what is often a tedious and imprecise process, to a more scalable, developper friendly and robust
part of your tests suite or data extraction mecanisms.

---

## Features

- **Playwright session management**: `WorkerSession` Inject the Playwright context, pages, and utility tools among all features executed in a worker.
- **Celery based task system**: Enjoy Celery's full functionnlities and configs for tasks with the `@feature` decorator.
- **Complex workflows**: support for chains and groups of tasks, with sequences managed automatically.
- **Smart tools for Playwright**: navigate, inspect, interact and wait modules gathers methods that facilitates implementing routines.
- **CLI**: run workflows or tasks from the terminal.
- **Isolated browser profiles**: manage profiles to prevent conflicts between workers and the main playwright processes.

---

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install chanina
```

or

```bash
poetry new my-chanina-project
cd my-chanina-project
poetry add chanina
poetry install
```

---

## Running Workers

Running the worker is done via the CLI. 
After indicating the path to the app, you have to precise the "-c" flags, and every arguments after will be passed to celery.

```bash
chanina -a path_to_myapp:app -c --loglevel=info --other-celery-conf=value ...
```

---

## Usage

### Build a basic feature 


```python
@app.feature("my_task")
def do_something(session: WorkerSession, args: dict):
    # session is the shared WorkerSession containing the current page and utilities
    page = session.new_page()
    session.goto(page, "https://example.com")
    session.close_page(page)
```

The first parameter of the feature's function is always the WorkerSession object.

!! Except when using the celery argument 'bind=True' parameter for the task, in which case the first parameter
is the instance of the class.


### Create and execute workflows  

A workflow is a file in which you can construct a sequence of features and specifies arguments.
The workflow has two main sections : 'steps' and 'instance'.

- The 'steps' section are the features you want to gather in the worker, their identifier, flow_id and flow_type.
If you pass args to a step defined here then it will be the default args passed to every instances.

- The 'instances' section is where you orchestrate the order in which the features are added to the flow_type, and the arguments they are running with. 
The args you pass there update the base args definied in the steps if one was defined.

Example:

If you have a 'extract_html' feature, and you add it in your workflow, you can add as much instance of it as you need page
to extract_html from, passing the page url in the 'args' key.

- Every step has a 'flow_type' argument, that can be 'chain' or 'group', and will determine the kind of celery task it will be.

**NOTE**

The sequence is built in the order of the instances in the file.
'group' task will be run FIRST and are non blocking for the rest of the sequence.
In the workflow example underneath, we can imagine that the flow_type 'group' of the task 'save_to_mongodb' is because the task
is a while loop running in parallel which saves in the db what the 'check_post' task is parsing.


Here is an example of a workflow file :

```yaml
steps
    - identifier: login_to_platform,
      args: 
        password: password1234
        username: Joseph S
      flow_type: chain

    - identifier: check_post
      flow_type: chain

    - identifier: save_in_mongodb
      args: 
        user: mongo_user 
        pw: password1234
        host: localhost
        port 27017
      flow_type: group

instances
    - check_post
      args:
        post_url: https://instagram.com/p/publication1
      args:
        post_url: https://instagram.com/p/publication2
      args:
        post_url: https://instagram.com/p/publication3
```

### Use the CLI  

Tasks can be ran with the CLI, please use 'python -m chanina --help' to learn more.

```bash
    $ python -m chanina login_workflow.yaml --app path_to_myapp:app --arguments password=$PASSWORD username=$USERNAME
```

You can also manually run a task if your worker is still up

```bash
    $ python -m chanina --task check_post --app path_to_myapp:app --arguments post_url="https://www.instagram.com/p/another-publication-not-in-the-workflow"
```

---

## License

For now this project has no Licence, i'm working on it.

