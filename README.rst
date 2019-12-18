Sprints
=============================

App for tracking sprint commitments, vacations and spillovers.

.. image:: https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg
     :target: https://github.com/pydanny/cookiecutter-django/
     :alt: Built with Cookiecutter Django

:License: AGPL-3.0

Overview
========

Sprint Planning Dashboard
-------------------------

Listing cells
^^^^^^^^^^^^^

On the main view there is the list of the cells. They are retrieved by looking for Jira boards with `JIRA_SPRINT_BOARD_PREFIX` prefix.

Cell's dashboard
^^^^^^^^^^^^^^^^

Estimations
~~~~~~~~~~~
The basic idea for calculating estimations is the following:

1. `SPRINT_HOURS_RESERVED_FOR_MEETINGS` hours are reserved for the meetings for each sprint.
2. `SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT` hours are reserved for epic management for each sprint.
3. 1 hour is planned for reviewing each task with <= 3 story points. For bigger tasks, 2 hours are reserved.
4. Each of these defaults can be overridden for each ticket by putting the following in the ticket’s description:
    a) [~{JIRA_BOT_USERNAME}]: plan `<time>` per sprint for epic management
    b) [~{JIRA_BOT_USERNAME}]: plan `<time>` per sprint for this task
    c) [~{JIRA_BOT_USERNAME}]: plan `<time>` for reviewing this task

**Note**: The `time` should match the following regexp:

.. code::

    (?:(?P<hours>\d+)\s?h.*?)?\s?(?:(?P<minutes>\d+)\s?m.*?)?

So anything like 1h 30m, 1h or 30m will work.

Dashboard
~~~~~~~~~
For each member of the cell this view displays:

1. Assignee, reviewer, upstream and epic-related hours for the present and upcoming sprint.
2. Tickets that are missing an estimation.
3. Scheduled vacations for the upcoming sprint, which are retrieved from the Google Calendar events that match `GOOGLE_CALENDAR_VACATION_REGEX`. Partial vacations (based on the time of the meeting for each person’s day) are retrieved from the `GOOGLE_AVAILABILITY_RANGE` of the `GOOGLE_CONTACT_SPREADSHEET` using the `GOOGLE_AVAILABILITY_REGEX`. The minus (-) suffix there indicates that the member’s timezone is UTC-X. This is taken into account if user’s workday spans over two days in UTC (i.e. start hour is after end hour).
4. Committed time, which is the sum of all estimation hours.
5. Goal for the next sprint, which is calculated by summing up user's commitments for each day of the sprint and subtracting `SPRINT_HOURS_RESERVED_FOR_MEETINGS` and `Vacation` hours from it.
6. Remaining time, which is the result of `Goal` - `Committed`.

User's dashboard
~~~~~~~~~~~~~~~~
This view shows all assigned (as `Assignee` or `Reviewer 1`) tickets of the user with:

1. Task's key (you can hover over it to see the ticket's name)
2. User's role
3. Current status of the ticket
4. Remaining time for the current user
5. Sprint indicator (active or future one)
6. Epic/Story indicator

Caching
~~~~~~~
After you refresh the board for the second time, you’ll immediately see cached data **and a spinner showing that it’s being reloaded**. This makes using the dashboard much smoother.


Creating new sprints
~~~~~~~~~~~~~~~~~~~~~~
In case when a user needs to schedule tickets for sprints that haven’t been created yet, they can press `Create Next Sprint` to create a new one for the currently viewed cell.

Completing sprints
~~~~~~~~~~~~~~~~~~~~~~
To complete a sprint, you need to have `Staff status` permissions.
The main idea behind this is that sprints are not shared by cells - you need to have separate sprint for each one. You can press the `Complete Sprint` button on the cell's dashboard to schedule a Celery task with the following pipeline:

1. Upload spillovers.
    This uploads all spillovers to the `GOOGLE_SPILLOVER_SPREADSHEET`. The following rows are filled in the spreadsheet:

    a) Ticket
        The key of the ticket.
    b) Status
        The status of the ticket at the moment of ending the sprint.
    c) Sprint
        The active sprint (the one that is currently being ended).
    d) Assignee
        The assignee, for whom the spillover is being counted.
    e) Reviewer 1
    f) Reviewer 2
    g) Reporter
    h) Story Points
    i) Estimated time
        The initial estimation of the ticket (in hours).
    j) Remaining time
        The remaining time for the ticket (in hours).
    k) Reason for the spillover
        The reason of the spillover is retrieved from the comments made within the active sprint. The assignees should provide it with a comment matching the following regexp: ```[~{JIRA_BOT_USERNAME}\]: <spillover>(.*)<\/spillover>```. In case of multiple occurrences of comments matching this regexp, only the last one is taken into account. In case of no occurrences of such comments, the Jira bot will create a comment defined in `SPILLOVER_REMINDER_MESSAGE`.

    If the team members have achieved a clean sprint (without spillovers), they can post some hints on the ticket with the `SPRINT_MEETINGS_TICKET` name by adding a comment matching the spillover reason regexp (provided above). In case of no such comment, they will be reminded on the ticket with `SPILLOVER_CLEAN_HINTS_MESSAGE` comment. It's possible to disable the pings for specific users by adding them to `SPILLOVER_CLEAN_SPRINT_IGNORED_USERS` (this can be useful for people that are members of multiple cells, as they will be pinged on each cell-specific ticket).
2. Upload commitments.
    The `goal` of each user from the dashboard is uploaded to the cell-specific commitments sheet of the `GOOGLE_SPILLOVER_SPREADSHEET`.
3. Move archived issues out of the active sprint.
    There has been a bug before that disallowed completing the sprint if it had archived issues, so we're moving all of them out of the active sprint.
4. Close the active sprint.
5. Move issues from the closed sprint to the next one.
6. Open the next sprint.
7. Create role-specific tasks for the sprint after next.
    The assignees for these tickets are retrieved from the `GOOGLE_ROTATIONS_RANGE` defined within `GOOGLE_ROTATIONS_SPREADSHEET`. The format of this document is the following:

    a) First column contains sprint number (you can create multiple role tasks for one week by dividing sprint into parts, e.g. `Sprint 100a, Sprint 100b` - each in a separate row).
    b) Next columns' headers contain role names prefixed by the full cell name (e.g. `Cell_1 FF`) and their fields contain assignees for the tickets.
    c) The "Date" column is omitted.

    The metadata (name, duration, story points) of these tickets is defined in `JIRA_CELL_ROLES`. Please see its docstring for the detailed explanation of its format.


Sustainability
--------------
The Sustainability Dashboard and Budget Dashboard (both described below) are aware of the sprint board’s current view (whether it’s showing cells/cell’s board/person’s board). Therefore, when you click on the cell’s name, the sustainability dashboard recalculates its data for displaying cell/person-related data only.

Sustainability Dashboard
^^^^^^^^^^^^^^^^^^^^^^^^
This view allows you to verify the assumptions described in `the "Cell Budgets" chapter of our handbook`_.
The key information here is the ratio of non-billable cell hours to billable cell hours. It is calculated in the following way:

    each cell ensures that it doesn't exceed a budget of 1h of internal/unbilled budget for every 2.5h the cell bills to clients.

.. _`the "Cell Budgets" chapter of our handbook`: https://handbook.opencraft.com/en/latest/cell_budgets/#cell-budgets


Overall sustainability
~~~~~~~~~~~~~~~~~~~~~~
Here we can view the sustainability combined for all existing projects. We are listing:

1. Total hours
    non-cell hours + cell hours
2. Billable hours
3. Total non-billable hours
    non-billable cell hours + non-billable non-cell hours
4. Percent of non-billable hours
    total non-billable hours / total hours

Cell's/User's sustainability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Here we can view the sustainability logged for a specific project or by a specific user. We are listing:

1. Total hours
2. Non-cell hours
    hours logged on non-billable non-cell tickets
3. Billable cell hours
4. Non-billable cell hours
    hours logged on non-billable cell-responsible tickets
5. Percent of non-billable hours
    ::

      non-billable_cell_hours / (billable_cell_hours + non-billable_cell_hours)
6. Remaining non-billable hours
    ::

      billable_cell_hours * MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO / (1 - MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO) - non-billable_cell_hours

Budget Dashboard
^^^^^^^^^^^^^^^^
This presents a list of all active accounts and the time spent on them from the beginning of the current year and the goal, based on the budget stored in the DB (see `Setting up budgets`_ for setup instructions). For each budget we are listing:

1. Account name with the prefix stripped for better readability.
2. Time spent from the beginning of the first year within the selected period.
    For `Overall` view the cell has green background when budget is on track and turns red when it's exceeded. This behavior is disabled on cell's and user's dashboards to reduce confusion.
3. Goal from the beginning of the first year within the selected period to the end of the next sprint.
    This field remains the same for all views, because budgets cannot be divided between cells.
4. Time spent during the selected period.
5. Time scheduled for the incomplete tickets in the current sprint.
6. Time scheduled for the tickets in the next sprint.
7. Time that can still be assigned for the next sprint. This value is the same for all views. Turns green if there are some hours.
    This field remains the same for all views, because any cell can use the remaining budget. The cell's background is green when remaining time is greater or equal 0, turns red when it's lower.
8. One of the following categories:
    a) Billable,
    b) Non-billable cell,
    c) Non-billable non-cell.


Setting up budgets
~~~~~~~~~~~~~~~~~~
To set up the budgets for the accounts you need to:

1. Log into the backend admin (by default it's http://localhost:8000/admin) with your superuser account.
2. Go to `Sustainability/Budgets`.
3. Add a new budget for the account.

The budgets are rolling, so these entries are perceived as *changes* of the budgets. It means that the budget for the account with the specified `name` will be `hours` (per month) up to the next change or current date.

    E.g. we have the account "Account - Security". From the beginning of 2019 we want the budget to be 100h/month, but from September to November (both inclusive) we want to raise it to 200h/month. From December and for the whole 2020 it should be lowered back to 100h/month. Therefore we need to create 3 entries via the Django admin:

    .. code:: javascript

        [{
            "name": "Account - Security",
            "date": January 2019,
            "hours": 100
        }, {
            "name": "Account - Security",
            "date": September 2019,
            "hours": 200
        }, {
            "name": "Account - Security",
            "date": December 2019,
            "hours": 100
        }]

    Side note: the `date` is a `DateField`, but the example is using simplified representation for brevity.

Setting up alerts
~~~~~~~~~~~~~~~~~
The alerts are defined in settings to be triggered with Celerybeat. It's possible to subscribe to specific cell or account alerts via Django admin.

It's also possible to specify addresses that will receive alerts for all existing cells and accounts. To do this, add email address to `NOTIFICATIONS_SUSTAINABILITY_EMAILS` environment variable.

For sustainability
******************
Alerts are sent when the ratio of non-billable cell hours to billable hours exceeds `MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO`.

By default these alerts are not being sent. To enable them:

1. Log into the backend admin (by default it's http://localhost:8000/admin) with your superuser account.
2. Go to `Sustainability/Cells`.
3. Add new cell.
4. Optionally add comma-separated email addresses that will receive alerts.

For budgets
***********
Alerts are sent when time spent from the beginning of the first year within the selected period is greater than the goal from the beginning of the current year to the end of the next sprint.

Alerts are sent by default to emails specified in `MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO`. To subscribe only to specific accounts:

1. Log into the backend admin (by default it's http://localhost:8000/admin) with your superuser account.
2. Go to `Sustainability/Accounts`.
3. Add new account.
4. Specify comma-separated email addresses that will receive alerts.

Settings
--------

Moved to settings_.

.. _settings: http://cookiecutter-django.readthedocs.io/en/latest/settings.html

Basic Commands
--------------

Running locally with Docker
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open a terminal at the project root and run the following for local development::

    $ docker-compose -f local.yml up

The web application is accessible at http://localhost:8000.

For the first time you will need to run migrations with::

    $ docker-compose -f local.yml run --rm django python manage.py migrate

You can also set the environment variable `COMPOSE_FILE` pointing to `local.yml` like this::

    $ export COMPOSE_FILE=local.yml

And then run::

    $ docker-compose up

Please see cookiecutter-django docs for more information about running locally `with Docker`_ or `without it`_.

.. _`with Docker`: https://cookiecutter-django.readthedocs.io/en/latest/developing-locally-docker.html
.. _`without it`: https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html

Setting Up Your Users
^^^^^^^^^^^^^^^^^^^^^

* To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

* To create an **superuser account**, use this command::

    $ docker-compose -f local.yml run --rm django python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

Type checks
^^^^^^^^^^^

Running type checks with mypy:

::

  $ docker-compose -f local.yml run django mypy sprints

Test coverage
^^^^^^^^^^^^^

To run the tests, check your test coverage, and generate an HTML coverage report::

    $ docker-compose -f local.yml run django coverage run -m pytest
    $ docker-compose -f local.yml run django coverage html

The results will be available in the `htmlcov/index.html`. You can open it with your browser.

Running tests with py.test
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  $ docker-compose -f local.yml run django pytest

Live reloading and Sass CSS compilation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Moved to `Live reloading and SASS compilation`_.

.. _`Live reloading and SASS compilation`: http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html



Celery
^^^^^^

This app comes with Celery.

To run a celery worker:

.. code-block:: bash

    cd sprints
    docker-compose -f local.yml run django celery -A config.celery_app worker -l info

Please note: For Celery's import magic to work, it is important *where* the celery commands are run. If you are in the same folder with *manage.py*, you should be right.





Sentry
^^^^^^

Sentry is an error logging aggregator service. You can sign up for a free account at  https://sentry.io/signup/?code=cookiecutter  or download and host it yourself.
The system is setup with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.


Deployment
----------

The following details how to deploy this application.



Docker
^^^^^^

See detailed `cookiecutter-django Docker documentation`_.

.. _`cookiecutter-django Docker documentation`: http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html
