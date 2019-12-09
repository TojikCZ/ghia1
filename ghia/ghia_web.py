#!/bin/python
import configparser

import flask
from flask import *
import os
import click
import hashlib
import hmac

from ghia.ghia_cmd import GHIASolver

REACT_TO = {"opened", "edited", "transferred", "reopened", "assigned", "unassigned", "labeled", "unlabeled"}

def load_config(path: str):
    """
    An alternative for loading configuration files without click

    :param path: a path to a configparser parsable file
    :return: a configparser object
    """
    try:
        with open(path) as file:
            cp = configparser.ConfigParser()
            cp.optionxform = str
            cp.read_file(file)
        if len(cp) < 2:
            raise click.BadParameter("incorrect configuration format")
        return cp
    except FileNotFoundError:
        raise click.BadParameter("incorrect configuration format")

def react_to_hook(app, json_data):
    """
    Configures the solver according to github provided json_data and the app config, then calls the solver to analyze and modify the assignees on the specified issue

    :param app: The flask app object
    :param json_data: The json data as received from the HTTP POST from github
    :return: nothing
    """
    reposlug = (json_data["repository"]["owner"]["login"], json_data["repository"]["name"])
    strategy = app.config.get("strategy", "append")
    dry_run = app.config.get("dry_run", False)
    ghia_solver = app.config["ghia_solver"]
    ghia_solver.change_config(reposlug, strategy, dry_run)

    issue = json_data["issue"]

    ghia_solver.assign_stuff_to_issue(issue)

def create_app(some_argument):
    """
    Initializes the flask app with configfiles set in env variable
    GHIA_CONFIG - the paths to config files separated by ":" There are two files expected. rules and auth config file

    :param some_argument: idk, but has to be there
    :return: the flask app object
    """
    app = flask.Flask(__name__)
    app.config.from_json("flask_config.json")

    ghia_config = os.environ.get("GHIA_CONFIG", default=None)

    if ghia_config is None:
        raise ValueError("supply GHIA_CONFIG environment variable")

    ghia_config_files = ghia_config.split(":")

    configs = list(map(load_config, ghia_config_files))

    auth_configs = [config for config in configs if "github" in config]
    rule_configs = [config for config in configs if "patterns" in config or "fallback" in config]


    if len(auth_configs) != 1:
        raise click.BadParameter("incorrect configuration format")
    if len(rule_configs) > 1:
        raise click.BadParameter("incorrect configuration format")
    if "token" not in auth_configs[0]["github"]:
        raise click.BadParameter("incorrect configuration format")

    app.config["auth"] = auth_configs[0]["github"]

    ghia_solver = GHIASolver(auth_configs[0], rule_configs[0], ("foo", "bar"))
    app.config["ghia_solver"] = ghia_solver

    user_patterns = ghia_solver.get_user_patterns()
    fallback_label = ghia_solver.get_fallback_label()

    app.config["user_patterns"] = user_patterns
    app.config["fallback_label"] = fallback_label

    secret = app.config["auth"].get("secret", None)

    user_info = ghia_solver.hubcom.get_user_info()

    app.config["user_info"] = user_info

    @app.route("/", methods=["GET"])
    def index():
        """
        Draws a templated page showing the current loaded configuration

        :return: http response
        """
        return render_template("homepage.html", username=user_info["login"], user_patterns=user_patterns, fallback_label=fallback_label)

    @app.route("/", methods=["POST"])
    def webhook():
        """
        Reacts to a webhook from github, that means it confirms that the message digest matches the one provided in the header of the request
        This digest is obtained as a sha1 HMAC using a configured secret. This secret is set in github settings and in the auth config file
        then confirms it is the right webhook named "issues" and the action is one of the specified in REACT_TO and the issue is open
        and if everything checks out it lets the function `react_to()` try and assign users according to configuration

        :return: Flask app object
        """
        try:
            if secret is not None:
                received_signature = request.headers['X-Hub-Signature'].split("sha1=")[1]

                key = bytes(app.config["auth"]["secret"], 'UTF-8')
                message = bytes(request.get_data(as_text=True), "UTF-8")

                digester = hmac.new(key, message, hashlib.sha1)
                computed_signature = digester.hexdigest()

                if received_signature != computed_signature:
                    raise RuntimeError("bad secret or received signature")

            json_data = request.get_json()

            if (request.headers["X-GitHub-Event"] == "issues" and
                json_data["action"] in REACT_TO and
                    json_data["issue"]["state"] == "open"):
                react_to_hook(app, json_data)
            return ("", 200, None)
        except Exception as e:
            print(e)
            return ("", 403, None)
    return app


if __name__ == "__main__":
    create_app("foo").run(debug=True)
