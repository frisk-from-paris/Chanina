Application
--------------------

Declaring an app
""""""""""""""""

*This is how you would declare an app instance.*

.. literalinclude:: ../../src/chanina/examples/basic_usage.py
   :language: python
   :lines: 1-29


*Running the worker ...*

.. code-block:: bash

    $ python -m chanina -a path_to_app:app


*Running a default feature as a single task.*

.. code-block:: bash

   $ python -m chanina -a path_to_app:app --task chanina.list_features


*Write a workflow.*

.. code-block:: yaml

   steps:
        - identifier: is_element_clickable
        flow_type: chain
        flow_id: html_elements

   instances:
       is_element_clickable:
       - link: https://recette.xmco.fr
         uri: page_1
         element: button
       
       - link: https://recette.xmco.fr
         uri: page_2
         element: div
         class: bootstrap-menu-item


This yaml file is a workflow. The 'steps' is the declarative section of the file. And the 'instances' is individual instances of a task
that will be created for one step.

*Run the workflow*

.. code-block:: bash

   $ python -m chanina -a path_to_app:app my-workflow.yaml


This command will now sends 2 instances of the 'is_element_clickable' feature to the broker.


Worker specificities
""""""""""""""""""""

The Chanina worker is a Celery worker wrapped and safely injected with a WorkerSession object.

