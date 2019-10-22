#!/bin/python
import configparser

import flask
import requests
from flask import *
import os
import click
import hashlib
import hmac

from ghia_cmd import get_user_patterns, get_fallback_label, assign_stuff_to_issue, GhiaParams

from dotenv import load_dotenv

load_dotenv('.env')

REACT_TO = set(("opened", "edited", "transferred", "reopened", "assigned", "unassigned", "labeled", "unlabeled"))

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
    ghia_params = GhiaParams(reposlug, strategy, dry_run)

    issue = json_data["issue"]

    user_patterns = app.config["user_patterns"]
    fallback_label = app.config["fallback_label"]

    session = app.config["session"]

    assign_stuff_to_issue(issue, user_patterns, fallback_label, session, ghia_params)



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
if "token" not in auth_configs[0]["github"] or "secret" not in auth_configs[0]["github"]:
    raise click.BadParameter("incorrect configuration format")

app.config["auth"] = auth_configs[0]["github"]
user_patterns = get_user_patterns(rule_configs[0])
fallback_label = get_fallback_label(rule_configs[0])

token = app.config["auth"]["token"]
secret = app.config["auth"]["secret"]

session = requests.Session()
session.headers = {'User-Agent': 'Python', 'Authorization': f'token {token}'}

app.config["session"] = session

r = session.get('https://api.github.com/user')
user_info = r.json()

app.config["user_info"] = user_info


app.config["user_patterns"] = user_patterns
app.config["fallback_label"] = fallback_label

@app.route("/", methods=["GET"])
def index():
    return render_template("homepage.html", username=user_info["login"], user_patterns=user_patterns, fallback_label=fallback_label)

@app.route("/", methods=["POST"])
def webhook():
    #  Nobody told me I should support unsecured pings, but the same people made a test case for it.
    #  They told me to follow the documentation which doesn't mention this.
    #  This wastes my time!
    #  So for you, here goes my special if check
    if request.headers["X-GitHub-Event"] == "ping" and \
            'X-Hub-Signature' not in request.headers:
        return ("", 200, None)
    #  I don't know what i should take out of this, where is the greater good in this?
    #  But you made my day worse for sure. Thank you

    try:
        received_signature = request.headers['X-Hub-Signature'].split("sha1=")[1]

        key = bytes(app.config["auth"]["secret"], 'UTF-8')
        message = bytes(request.get_data(as_text=True), "UTF-8")

        digester = hmac.new(key, message, hashlib.sha1)
        computed_signature = digester.hexdigest()

        if received_signature != computed_signature:
            raise RuntimeError("bad checksum")

        json_data = request.get_json()

        if request.headers["X-GitHub-Event"] == "issues" and\
                json_data["action"] in REACT_TO:
            react_to_hook(app, json_data)
        return ("", 200, None)
    except:
        return ("", 400, None)


if __name__ == "__main__":
    app.run(debug=True)
