.. GHIA documentation master file, created by
   sphinx-quickstart on Thu Dec  5 22:20:06 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to GHIA's documentation!
================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   doctests
   modules

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Introduction
============

Description
-----------

This project is a solution to a homework assignment, hence the garbage code quality

The app is used to automatically assign issues to specific users based on the content of a github issue.
To determine if an issue can be assigned to a user, users are associated with regular expressions tied to a specific part of an issue body that will be checked.
For example: any issue containing the word alicorn in its title goes to `M.A.Larson <https://mlp.fandom.com/wiki/M._A._Larson>`_
A user is considered assignable if any one of the associated regexps matches.
If no users are considered assignable, the issue can be given a fallback label.

The configuration file looks like this:
 .. code-block::

    [patterns]
    username=
        title:regexp
        text:other_regexp
        text:another_regexp
        label:not_the_same_regexp
        any:totally_different_regexp
    anotherusername=
        any:whatever_regexp

    [fallback]
    label=Need assignment

As you can see, there can be multiple of the same type like "text" which is valid

This app also needs credentials to be able to make any changes.
This means that a github account that has collaborator access to the repo you want to manage is required.
You need to generate an api key with repo scope checked in github settings -> developer settings -> personal access tokens
This token is then stored in another configparser file looking like so

 .. code-block::

    [github]
    token: verysecretstuffgoeshere

The app is split into two parts:

* the command line utility that can be run manually or scheduled through automation software to run periodically
* the web version that can be deployed and triggered through github webhooks

**Webhooks** react to an event in a github repository. They can be filtered by an event type and secured by a shared secret.

This app supports webhooks. For those to be secure the same secret has to be configured on both sides.
For this, the authentication config contains another field: `secret: verysecretstuffgoeshere`
On github, the secret can be set under your_repo -> repo settings -> webhooks -> your_webhook -> secret

There are multiple modes of operation:

* **append** - which appends all unassigned assignable users
* **set** - which appends the assignable users only if there are none assigned already
* **change** - which removes all that are not assignable and assigns those who are

Those can be set in the cmd line argument and in the flask config in `ghia_root/ghia/flask_config.json`

There is also an option for dry running, which does not make any actual changes, but says which would be done.

For the command line version to know which repo is to be affected, a reposlug is expected.
It consists of two parts owner_username and repo_name separated by a slash. For example: `erkin/ponysay`

Example use of the command line: `ghia --strategy append --config-rules rules.cfg --config-auth auth.cfg erkin/ponysay`

The web version is running at `tojik.pythonAnywhere.com <https://tojik.pythonanywhere.com/>`_

Installation
------------

In the ideal world installation would be done through `pip install ghia`.
Because this is a useless school project it's `pip install -i https://test.pypi.org/simple/ ghia-joziftom`

you can also run `python setup.py install`

For deployment of the flask app, environment variable GHIA_CONFIG has to be present and has to contain paths to the rule config and the credential config separated by a colon ":"
Then follow the instructions for deployment on your platform

for PythonAnywhere the wsgi file should look like so:

 .. code-block:: python

    import sys

    project_home = u'/home/username/ghia_root_directory'
    if project_home not in sys.path:
        sys.path = [project_home] + sys.path

    import os
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_home, '.env'))

    # import flask app but need to call it "application" for WSGI to work
    from ghia import create_app
    application = create_app(None)

and the .env in ghia_root will need to contain the GHIA_CONFIG variable export for example:
`export GHIA_CONFIG=credential.cfg:rules.cfg`

