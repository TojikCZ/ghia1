#!/bin/python
import configparser

import requests
import click
import re

ADD = "+"
REMOVE = "-"
LEAVE = "="

class GhiaParams:

    def __init__(self, reposlug, strategy="append", dry_run=False):
        self.reposlug = reposlug
        self.owner, self.repo = self.reposlug
        self.strategy = strategy
        self.dry_run = dry_run

def validate_reposlug(ctx, param, slug: str):
    parts = slug.split("/")
    if not (len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0):
        raise click.BadParameter("not in owner/repository format")
    return parts[0], parts[1]


def validate_file(ctx, param: click.core.Option, path: str):
    try:
        cp = configparser.ConfigParser()
        cp.optionxform = str
        cp.read_file(path)
    except FileNotFoundError:
        raise click.BadParameter("incorrect configuration format")
    if len(cp) < 2:
        raise click.BadParameter("incorrect configuration format")
    return cp


def write_error(message: str, indentation=0):
    click.secho(indentation*" " + "ERROR: ", bold=True, nl=False, fg="red", err=True)
    click.secho(message, err=True)


def write_fallback(message: str):
    click.secho("   FALLBACK: ", bold=True, nl=False, fg="yellow")
    click.secho(message)


def does_any_pattern_match(pattern_list, string):
    for pattern in pattern_list:
        if pattern.search(string):
            return True
    return False


def namedrop_assignee(action, username):
    if action == ADD:
        click.secho("   + ", nl=False, fg="green", bold=True)
    if action == REMOVE:
        click.secho("   - ", nl=False, fg="red", bold=True)
    if action == LEAVE:
        click.secho("   = ", nl=False, fg="blue", bold=True)
    click.echo(username)


def update_assignee(action, username, session: requests.Session, owner, repo, issue_number):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/assignees"
    if action == ADD:
        r = session.post(url, json={"assignees": [username]})
        if r.status_code != 201:
            write_error(f"Could not update issue {owner}/{repo}#{issue_number}", 3)
            return False
    elif action == REMOVE:
        r = session.delete(url, json={"assignees": [username]})
        if r.status_code != 200:
            write_error(f"Could not update issue {owner}/{repo}#{issue_number}", 3)
            return False
    return True


def update_users(action, user_list, session, issue_number, ghia_params):
    for username in user_list:
        if not ghia_params.dry_run:
            if update_assignee(action, username, session, ghia_params.owner, ghia_params.repo, issue_number):
                namedrop_assignee(action, username)
        else:
            namedrop_assignee(action, username)


def get_next_page_link_from_request(request):
    next_page_regexp = re.compile("<([^>]*)>; rel=\"next\"")

    next_page_match = None
    if "Link" in request.headers:
        next_page_match = next_page_regexp.search(request.headers["Link"])

    if next_page_match is not None:
        return next_page_match.group(1)
    return None


def get_user_patterns(config_rules):
    user_patterns = {}
    for username, pattern_string in config_rules["patterns"].items():

        pattern_dict = {"title": [], "text": [], "label": [], "any": []}

        for pattern_line in pattern_string.split("\n"):

            if len(pattern_line) == 0:
                continue

            pattern_name, pattern = pattern_line.split(":", maxsplit=1)
            pattern_dict[pattern_name].append(re.compile(pattern, re.IGNORECASE))

        user_patterns[username] = pattern_dict
    return user_patterns


def get_fallback_label(config_rules):
    if "fallback" in config_rules and "label" in config_rules["fallback"]:
        return config_rules["fallback"]["label"]
    else:
        return None


def get_issue_list(session, owner, repo):
    issue_list = []
    r = session.get(f"https://api.github.com/repos/{owner}/{repo}/issues")
    if r.status_code != 200:
        write_error(f"Could not list issues for repository {owner}/{repo}")
        exit(10)
    else:
        issue_list.extend(r.json())
        next_page_url = get_next_page_link_from_request(r)
        while next_page_url is not None:
            r = session.get(next_page_url)
            issue_list.extend(r.json())
            next_page_url = get_next_page_link_from_request(r)
    return issue_list


def assign_stuff_to_issue(issue, user_patterns, fallback_label, session, ghia_params):
    # ---- GET ASSIGNED USERS ----

    sorted_assigned_users = [user["login"] for user in issue["assignees"]]
    sorted_assigned_users.sort(key=str.casefold)

    assigned_users = set()
    assigned_users.update(sorted_assigned_users)

    # ---- WRITE ISSUE NAME LINE

    click.secho("-> ", nl=False)
    click.secho(f"{'/'.join(ghia_params.reposlug)}#{issue['number']} ", nl=False, bold=True)
    click.secho(f"({issue['html_url']})")

    # ---- GET ASSIGNABLE USERS USING REGEXP ----

    assignable_users = set()
    issue_labels = [label["name"] for label in issue["labels"]]

    for username, pattern_dict in user_patterns.items():

        if does_any_pattern_match(pattern_dict["title"], issue["title"]) or \
                does_any_pattern_match(pattern_dict["text"], issue["body"]) or \
                does_any_pattern_match(pattern_dict["any"], issue["title"]) or \
                does_any_pattern_match(pattern_dict["any"], issue["body"]):
            assignable_users.add(username)

        for label in issue_labels:
            if does_any_pattern_match(pattern_dict["label"], label) or \
                    does_any_pattern_match(pattern_dict["any"], label):
                assignable_users.add(username)

    # ---- GET ADDABLE, REMOVABLE AND LEAVABLE SORTED USER LISTS ----

    sorted_addable_users = list(assignable_users - assigned_users)
    sorted_addable_users.sort(key=str.casefold)

    sorted_removable_users = list(assigned_users - assignable_users)
    sorted_removable_users.sort(key=str.casefold)

    if ghia_params.strategy == "change":
        sorted_leavable_users = list(assignable_users.intersection(assigned_users))
        sorted_leavable_users.sort(key=str.casefold)
    else:
        sorted_leavable_users = sorted_assigned_users

    # ---- MAKE_CHANGES / OUTPUT ----

    for username in sorted_leavable_users:
        namedrop_assignee(LEAVE, username)

    if ghia_params.strategy == "append":
        update_users(ADD, sorted_addable_users, session, issue["number"], ghia_params)

    elif ghia_params.strategy == "set":
        if not assigned_users:
            update_users(ADD, sorted_addable_users, session, issue["number"], ghia_params)

    elif ghia_params.strategy == "change":
        update_users(REMOVE, sorted_removable_users, session, issue["number"], ghia_params)
        update_users(ADD, sorted_addable_users, session, issue["number"], ghia_params)

    # ---- FALLBACK LABEL ----

    if not assignable_users and not assigned_users:
        if fallback_label:
            if fallback_label in issue_labels:
                write_fallback(f"already has label \"{fallback_label}\"")
            else:
                if not ghia_params.dry_run:
                    issue_labels.append(fallback_label)
                    r = session.post(f"https://api.github.com/repos/{ghia_params.owner}/{ghia_params.repo}/issues/{issue['number']}/labels",
                                     json={"labels": issue_labels})
                    if r.status_code != 200:
                        write_error(f"Could not update issue {ghia_params.owner}/{ghia_params.repo}#{issue['number']}", 3)
                write_fallback(f"added label \"{fallback_label}\"")


@click.command()
@click.option("-s", "--strategy", default="append", show_default=True, type=click.Choice(["append", "set", "change"]),
              help="How to handle assignment collisions.")
@click.option("-d", "--dry-run", is_flag=True,
              help="Run without making any changes.")
@click.option("-a", "--config-auth", required=True, type=click.File("r"), callback=validate_file,
              help="File with authorization configuration.")
@click.option("-r", "--config-rules", required=True, type=click.File("r"), callback=validate_file,
              help="File with assignment rules configuration.")
@click.argument("reposlug", callback=validate_reposlug, required=True)
def ghia_cmd(strategy, dry_run, config_auth, config_rules, reposlug):
    """CLI tool for automatic issue assigning of GitHub issues"""
    ghia(reposlug, config_auth, config_rules, strategy, dry_run)


def ghia(reposlug, config_auth, config_rules, strategy="append", dry_run=True):
    # ---- SETUP ----

    ghia_params = GhiaParams(reposlug, strategy, dry_run)

    token = config_auth["github"]["token"]

    session = requests.Session()
    session.headers = {'User-Agent': 'Python', 'Authorization': f'token {token}'}

    # ----  REGEXP CONFIG ----

    fallback_label = get_fallback_label(config_rules)
    user_patterns = get_user_patterns(config_rules)

    # ---- ISSUES ----

    issue_list = get_issue_list(session, ghia_params.owner, ghia_params.repo)

    for issue in issue_list:

        assign_stuff_to_issue(issue, user_patterns, fallback_label, session, ghia_params)


if __name__ == "__main__":
    ghia_cmd()
