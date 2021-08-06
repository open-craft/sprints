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
3. Reserved time for reviewing is defined in `SPRINT_HOURS_RESERVED_FOR_REVIEW` as a json dict, where you can define the review time for any
   amount of story points. Jira tickets without story points will have a "null" value here, so the default behavior can be specified by defining
   this as a key. Example configuration:

   .. code::

        SPRINT_HOURS_RESERVED_FOR_REVIEW = {
            "null": 2,
            "0": 0.5,
            "1.9": 1,
            "2": 3,
            "5.1": 6
        }

   Here we are defining that:

   1. If not story points are set for an issue, it will reserve 2 hours for its review.
   2. If 0 story points are set for an issue, it will reserve 0.5 hours for its review.
   3. If 1.9 story points are set for an issue, it will reserve 1 hour for its review.
   4. If 2 story points are set for an issue, it will reserve 3 hours for its review.
   5. If 5.1 story points are set for an issue, it will reserve 6 hours for its review.
   6. If the ticket has an amount of story points that is not defined in the `SPRINT_HOURS_RESERVED_FOR_REVIEW` setting,
      then it will use the review time for the nearest number of story point defined. For example:
       - If 3 story points are set for an issue, it will reserve, 3 hours for its review, as the closest number of story points
         defined is 2
       - If more than 5.1 story points (6, 10, 20, etc.) are defined for an issue, it will reserve 6 hours for its review,
         because the closest story points value defined is 5.1

   **The "null" value is REQUIRED to be defined in `SPRINT_HOURS_RESERVED_FOR_REVIEW`.**

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
7. Toggles:
    a) Ongoing work. Default: true.
        This is useful to for planning the next sprint upfront by making an assumption that all work from the current sprint will be completed on time.
    b) Accepted (flagged) tickets. Default: false.
        If tickets are preassigned and flagged, then the assignees can use this option to determine whether they need to pass on some tickets.

User's dashboard
~~~~~~~~~~~~~~~~
This view shows all assigned (as `Assignee` or `Reviewer 1`) tickets of the user with:

1. Task's key (you can hover over it to see the ticket's name)
2. User's role
3. Current status of the ticket
4. Remaining time for the current user
5. Sprint indicator (active or future one)
6. Epic/Story indicator

Note: if a ticket is flagged, then its row's background will be yellow.

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
8. Trigger the ``new sprint`` webhooks.
    Please see the `Setting up webhooks`_ section for more information about this.
9. Release the sprint completion lock and clear the cache related to sprint start date.
    The sprint completion task is using a Redis lock for eliminating race conditions if a task is scheduled more than once.


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

.. raw:: html

    <div id="column-overall-total-hours"></div>

1. Total hours
    non-cell hours + cell hours

    .. raw:: html

        <div id="column-overall-billable-hours"></div>
2. Billable hours
    .. raw:: html

        <div id="column-overall-non-billable-hours"></div>
3. Total non-billable hours
    non-billable cell hours + non-billable non-cell hours

    .. raw:: html

        <div id="column-overall-percent-of-non-billable-hours"></div>
4. Percent of non-billable hours
    total non-billable hours / total hours

Cell's/User's sustainability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Here we can view the sustainability logged for a specific project or by a specific user. We are listing:

.. raw:: html

    <div id="column-total-hours"></div>

1. Total hours
    .. raw:: html

        <div id="column-non-cell-hours"></div>
2. Non-cell hours
    hours logged on non-billable non-cell tickets

    .. raw:: html

        <div id="column-billable-cell-hours"></div>
3. Billable cell hours
    .. raw:: html

        <div id="column-non-billable-cell-hours"></div>
4. Non-billable cell hours
    hours logged on non-billable cell-responsible tickets

    .. raw:: html

        <div id="column-percent-of-non-billable-hours"></div>
5. Percent of non-billable hours
    .. raw:: html

        <div id="column-remaining-non-billable-hours"></div>

    ::

      non-billable_cell_hours / (billable_cell_hours + non-billable_cell_hours)
6. Remaining non-billable hours
    ::

      billable_cell_hours * MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO / (1 - MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO) - non-billable_cell_hours

Budget Dashboard
^^^^^^^^^^^^^^^^
This presents a list of all active accounts and the time spent on them from the beginning of the current year and the goal, based on the budget stored in the DB (see `Setting up budgets`_ for setup instructions). For each budget we are listing:

.. raw:: html

        <div id="column-budget"></div>

1. Account name with the prefix stripped for better readability.

    .. raw:: html

        <div id="column-ytd-spent"></div>
2. Time spent from the beginning of the first year within the selected period.
    For `Overall` view the cell has green background when budget is on track and turns red when it's exceeded. This behavior is disabled on cell's and user's dashboards to reduce confusion.

    .. raw:: html

        <div id="column-ytd-goal"></div>
3. Goal from the beginning of the first year within the selected period to the end of the next sprint.
    This field remains the same for all views, because budgets cannot be divided between cells.

    .. raw:: html

        <div id="column-period-spent"></div>
4. Time spent during the selected period.
    .. raw:: html

        <div id="column-period-goal"></div>
5. Goal for the selected period.
    This field remains the same for all views, because budgets cannot be divided between cells.

    .. raw:: html

        <div id="column-left-this-sprint"></div>
6. Time scheduled for the incomplete tickets in the current sprint.
    .. raw:: html

        <div id="column-next-sprint"></div>
7. Time scheduled for the tickets in the next sprint.
    .. raw:: html

        <div id="column-remaining-for-next-sprint"></div>
8. Time that can still be assigned for the next sprint. This value is the same for all views. Turns green if there are some hours.
    This field remains the same for all views, because any cell can use the remaining budget. The cell's background is green when remaining time is greater or equal 0, turns red when it's lower.

    .. raw:: html

        <div id="column-category"></div>
9. One of the following categories:
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

Setting up webhooks
~~~~~~~~~~~~~~~~~~~
The sprints app supports triggering webhooks on certain events. Currently the following events are supported:

1. 'new sprint' - Triggered at the end of the sprint completion process. It fires a webhook containing details of each member of the cell & their responsibilities in the new sprint. It reads permanent roles (Sprint Planning Manager etc.) from the ``HANDBOOK_ROLES_PAGE``, and temporary roles (Firefighter, Discovery Duty etc.) from the rotations spreadsheets. If the ``FEATURE_CELL_ROLES`` (disabled by default) environment variable is set to ``True`` it will cause an error and prevent the sprint from being completed if the permanent roles cannot be read from the handbook.

In order to setup receivers you first need to setup webhook events; to do that follow these steps:

1. Go to 'Webhook events' in your Django admin panel (http://your_site/admin/webhooks/webhookevent/).
2. Click 'Add webhook event' and create events based on the above mentioned list of events.

For now only the 'new sprint' event type is supported. More event types will be added in the future.

To create a new webhook receiver, follow these steps:

1. Make sure a 'Webhook Event' exists for your webhook (see the following section for the instructions).
2. Go to 'Webhooks' in the Django admin panel (http://your_site/admin/webhooks/webhook/).
3. Click 'Add Webhook'.
4. In Events, select one or multiple events to link to the webhook & enter a payload URL. If you'd like to send any extra headers with the request, you can specify them in the headers field using the JSON format.


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

Automation
----------
Sprints implement tasks that automate some parts of the sprint planning process. To enable automation, set the ``FEATURE_SPRINT_AUTOMATION`` env variable to ``True``.

Pinging people
^^^^^^^^^^^^^^^
The automations retrieve users responsible for a ticket. The following rules apply for this:
1. The assignee is included if the ticket is assigned.
2. The epic owner is included if the ticket is unassigned or if a task explicitly requests this.
3. The reporter is included if the ticket both:
- is unassigned,
- does not belong to an epic or the epic is unassigned.
4. If none of the above is present, the error is reported to Sentry.
A task determines whether the users will be pinged on the ticket (with an asynchronous comment) or via the Mattermost (with a synchronous message), depending on the urgency of this part of the sprint planning process.

Scheduling tasks
^^^^^^^^^^^^^^^^^
While completing the sprint, the automation tasks are scheduled for the new one. There are two types of supported tasks:
1. One-off - ran on a specific day of the sprint.
2. Periodic - ran hourly from a specific day of the sprint to either another day or until the end of the sprint.

You can see the scheduled tickets in the Django admin panel (http://your_site/admin/django_celery_beat/periodictask/).

Ticket planning
^^^^^^^^^^^^^^^^^^
These tasks relate to planning the tickets for the next sprint.

Handle task injections
~~~~~~~~~~~~~~~~~~~~~~
To make the sprint planning easier, we have introduced a ticket creation cutoff day. From this day of the sprint, it is no longer possible to add tickets to the next sprint. If the ticket needs to be added to the next sprint, then it's added to "Stretch Goals", and then it's picked up only if the cell has the capacity, as described in the `Task Insertion`_ section of our handbook.

If a ticket is added to the next sprint after the cutoff day, it will be automatically moved to the "Stretch Goals" sprint, then the ticket's reporter and the epic owner will be notified about this via a comment on the ticket.
To accept a sprint injection, a specific label (``injection-accepted`` by default) needs to be added to the ticket by the `Sprint Planning Manager`_.

This is a periodic task, which is running hourly from the cutoff day until the end of the sprint.

.. _`Task Insertion`: https://handbook.opencraft.com/en/latest/sprint_planning_agenda/#task-insertion
.. _`Sprint Planning Manager`: https://handbook.opencraft.com/en/latest/roles/#cell-sprint-planning-manager

Check if all tasks are ready for the next sprint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This task determines whether all tickets have the following attributes set:

1. Assignee.
2. Reviewer.
3. Story Points.

Each person, who has some incomplete tickets, will be pinged on Mattermost, with a list of these tickets, with sublists of their missing fields.

This is a one-off task, which runs at the beginning of the sprint's final day.

Find overcommitted people
~~~~~~~~~~~~~~~~~~~~~~~~~
This task uses Mattermost to ping people who have negative time left for the next sprint (i.e. are overcommitted).

This is a one-off task, which runs at the beginning of the sprint's final day.

Unflag tickets
~~~~~~~~~~~~~~
This task removes all "Impediment" flags from the tickets scheduled for the next sprint.

This is a one-off task, which runs at the end of the sprint.

Estimation session
^^^^^^^^^^^^^^^^^^^^
For estimating tickets, we are using the `Agile Poker`_ Jira app.

Creating sessions
~~~~~~~~~~~~~~~~~~~~
At the beginning of the sprint, a new session is created for each cell.

Note
****
Creating a session without issues causes some chaos in Jira, as the ``/session/async/{sessionId}/rounds/`` endpoint returns HTTP 500 in such case. It does not break other API calls, so operations like updating, closing, and deleting the session (via the API) work correctly. It makes the session unusable via the browser by breaking two views:
- estimation,
- configuration.
Therefore, the decision is to avoid adding the participants to the session until there are issues that can be added too. Assuming that the sessions are fully automated, and don't require any manual interventions in the beginning, this should not cause any troubles.

This is a one-off task, which runs at the beginning of the sprint. The email notification is not sent, because there are no participants.

Updating sessions
~~~~~~~~~~~~~~~~~
This task adds any tickets that have been added to the next sprint but are not present in the estimation session. It also adds participants, when there are tickets scheduled for the next sprint (please see the explanation above), or if a new member joins a cell.

Note
****
This does not override the manual additions to the session - i.e. if a ticket or user has been added manually to the session, then it will be retained, as it merges available issues and participants with the applied ones. However, any removed items (e.g. ticket scheduled for the next sprint or of a user, who is a member of the cell) will be added back automatically.

This is a periodic task, which is running hourly from the beginning of the sprint until the final day of the sprint. The participants are notified about each change via email, so they are aware of the unestimated tickets.

Closing sessions
~~~~~~~~~~~~~~~~
The session is closed for each cell before the sprint's final day. This triggers the `Moving estimates to tickets`_ task.

This is a one-off task, which runs at the beginning of the sprint. The participants are notified about this via email.

Moving estimates to tickets
~~~~~~~~~~~~~~~~~~~~~~~~~~~
This applies the average vote results from the closed estimation session to all tickets. In the case of a draw, the higher estimate is returned.

If there were no votes for a specific ticket, its assignee (or another responsible person) is notified.

.. _`Agile Poker`: https://marketplace.atlassian.com/apps/700473/agile-poker-for-jira-planning-estimation


Configuration variables
~~~~~~~~~~~~~~~~~~~~~~~
Please see the `configuration file`_ for a detailed description of these variables.

1. ``FEATURE_SPRINT_AUTOMATION``
2. ``SPRINT_ASYNC_TICKET_CREATION_CUTOFF_DAY``
3. ``SPRINT_ASYNC_INJECTION_LABEL``
4. ``SPRINT_ASYNC_INJECTION_SPRINT``
5. ``SPRINT_ASYNC_INJECTION_MESSAGE``
6. ``SPRINT_ASYNC_TICKET_FINAL_CHECK_DAY``
7. ``SPRINT_ASYNC_POKER_NEW_SESSION_MESSAGE``
8. ``SPRINT_ASYNC_POKER_NO_ESTIMATES_MESSAGE``
9. ``SPRINT_ASYNC_INCOMPLETE_TICKET_MESSAGE``
10. ``SPRINT_ASYNC_OVERCOMMITMENT_MESSAGE``


.. _`configuration file`: config/settings/base.py



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

