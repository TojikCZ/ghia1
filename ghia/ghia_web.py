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
    reposlug = (json_data["repository"]["owner"]["login"], json_data["repository"]["name"])
    strategy = app.config.get("strategy", "append")
    dry_run = app.config.get("dry_run", False)
    ghia_solver = app.config["ghia_solver"]
    ghia_solver.change_config(reposlug, strategy, dry_run)

    issue = json_data["issue"]

    user_patterns = app.config["user_patterns"]
    fallback_label = app.config["fallback_label"]

    session = app.config["session"]

    ghia_solver.assign_stuff_to_issue(issue)

def create_app(some_argument):
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
        return render_template("homepage.html", username=user_info["login"], user_patterns=user_patterns, fallback_label=fallback_label)

    @app.route("/", methods=["POST"])
    def webhook():
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
