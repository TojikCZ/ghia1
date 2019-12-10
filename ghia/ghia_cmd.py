#!/bin/python
import configparser
import re

import click
from ghia.github_communicator import RequestException, GithubCommunicator


class GHIASolver:
    ADD = 0
    REMOVE = 1
    LEAVE = 2

    def __init__(self, config_auth, config_rules, reposlug, strategy="append", dry_run=False):
        """
        Initializes the solver

        Strategy options are:
        append - adds new users to an issue
        set - sets users matching config if there are none set
        change - removes whoever is assigned and adds those matching config

        :param config_auth: Config parser object with auth config file open as specified in the homework assignment
        :param config_rules: Config parser object with rules config file open as specified in the homework assignment
        :param reposlug: A string containing f"{repo_owner}/{repo_name}"
        :param strategy: What strategy is to be used options: "append", "set", "change"
        :param dry_run: boolean saying whether changes are to be persisted or not
        """
        self.reposlug = reposlug
        self.owner, self.repo = self.reposlug
        self.strategy = strategy
        self.dry_run = dry_run
        self.config_rules = config_rules

        self.token = config_auth["github"]["token"]

        self.hubcom = GithubCommunicator(self.token, self.owner, self.repo)

        self.fallback_label = self.get_fallback_label()
        self.user_patterns = self.get_user_patterns()
        self.issue_list = []

    def solve(self):
        """
        Gets stuff done. Call after you are happy with the configuration of the solver

        :return: well thanks pycharm for generating this useless field. This method does not return anything useful
        """
        try:
            self.issue_list = self.hubcom.get_issue_list()
        except RequestException as e:
            exit(10)
            return
        for issue in self.issue_list:
            self.assign_stuff_to_issue(issue)

    def change_config(self, reposlug, strategy=None, dry_run=None):
        """
        Sets multiple things at once, otherwise it's a boring setter

        :param reposlug: A string containing f"{repo_owner}/{repo_name}"
        :param strategy: What strategy is to be used options: "append", "set", "change"
        :param dry_run: boolean saying whether changes are to be persisted or not
        """
        self.reposlug = reposlug
        self.owner, self.repo = self.reposlug

        if strategy is not None:
            self.strategy = strategy

        if dry_run is not None:
            self.dry_run = dry_run

    def get_user_patterns(self):
        """
        Prepares the data from the rule config

        :return: Dict[str "username", Dict[str "pattern name", list[re "regexp"]]]
                 for example: {"LittleshyFIM": {"title": ["derpy", "is"], "text": ["the"], "label": ["best"], "any": ["pony"]}}
        """
        user_patterns = {}
        for username, pattern_string in self.config_rules["patterns"].items():

            pattern_dict = {"title": [], "text": [], "label": [], "any": []}

            for pattern_line in pattern_string.split("\n"):

                if len(pattern_line) == 0:
                    continue

                pattern_name, pattern = pattern_line.split(":", maxsplit=1)
                pattern_dict[pattern_name].append(re.compile(pattern, re.IGNORECASE))

            user_patterns[username] = pattern_dict
        return user_patterns

    def get_fallback_label(self):
        """
        Gets the fallback label from the configuration rule file if there is such a thing. Otherwise returns None

        :return: string containing the label or None
        """
        if "fallback" in self.config_rules and "label" in self.config_rules["fallback"]:
            return self.config_rules["fallback"]["label"]
        else:
            return None

    def update_users(self, action, user_list, issue_number):
        """
        Makes the calls to update assignees

        :param action: specifies what will be done with users in the user list. One of self.ADD REMOVE LEAVE
        :param user_list: list of strings - usernames, to be affected
        :param issue_number: an issue number to be affected
        :return:
        """
        for username in user_list:
            if not self.dry_run:
                self.hubcom.update_assignee(action, username, issue_number)
                self.namedrop_assignee(action, username)
            else:
                self.namedrop_assignee(action, username)

    def does_any_pattern_match(self, pattern_list, string):
        """
        Checks if the string supplied matches at least one of the patterns in pattern list

        :param pattern_list: list of regexp patterns
        :param string: a string for the regexps to be matched against
        :return: boolean if match was found or not
        """
        for pattern in pattern_list:
            if pattern.search(string):
                return True
        return False

    def write_fallback(self, message: str):
        """
        Writes a fallback message with a four space indentation

        :param message: a fallback message string to write
        """
        click.secho("   FALLBACK: ", bold=True, nl=False, fg="yellow")
        click.secho(message)

    def namedrop_assignee(self, action, username):
        """
        Writes a symbol indicating what action will be done and the username provided

        :param action: one of `self.ADD self.REMOVE self.LEAVE`
        :param username: the str username
        :return: nothing
        """
        if action == self.ADD:
            click.secho("   + ", nl=False, fg="green", bold=True)
        if action == self.REMOVE:
            click.secho("   - ", nl=False, fg="red", bold=True)
        if action == self.LEAVE:
            click.secho("   = ", nl=False, fg="blue", bold=True)
        click.echo(username)

    def assign_stuff_to_issue(self, issue):
        """
        Mom's spaghetti
        Figures out which users are already assigned, which are to be assigned and calls correct functions depending on the strategy configured

        :param issue: an issue json as retrieved from github
        :return: nothing
        """
        # ---- GET ASSIGNED USERS ----

        sorted_assigned_users = [user["login"] for user in issue["assignees"]]
        sorted_assigned_users.sort(key=str.casefold)

        assigned_users = set()
        assigned_users.update(sorted_assigned_users)

        # ---- WRITE ISSUE NAME LINE

        click.secho("-> ", nl=False)
        click.secho(f"{self.owner}/{self.repo}#{issue['number']} ", nl=False, bold=True)
        click.secho(f"({issue['html_url']})")

        # ---- GET ASSIGNABLE USERS USING REGEXP ----

        assignable_users = set()
        issue_labels = [label["name"] for label in issue["labels"]]

        for username, pattern_dict in self.user_patterns.items():

            if self.does_any_pattern_match(pattern_dict["title"], issue["title"]) or \
                    self.does_any_pattern_match(pattern_dict["text"], issue["body"]) or \
                    self.does_any_pattern_match(pattern_dict["any"], issue["title"]) or \
                    self.does_any_pattern_match(pattern_dict["any"], issue["body"]):
                assignable_users.add(username)

            for label in issue_labels:
                if self.does_any_pattern_match(pattern_dict["label"], label) or \
                        self.does_any_pattern_match(pattern_dict["any"], label):
                    assignable_users.add(username)

        # ---- GET ADDABLE, REMOVABLE AND LEAVABLE SORTED USER LISTS ----

        sorted_addable_users = list(assignable_users - assigned_users)
        sorted_addable_users.sort(key=str.casefold)

        sorted_removable_users = list(assigned_users - assignable_users)
        sorted_removable_users.sort(key=str.casefold)

        if self.strategy == "change":
            sorted_leavable_users = list(assignable_users.intersection(assigned_users))
            sorted_leavable_users.sort(key=str.casefold)
        else:
            sorted_leavable_users = sorted_assigned_users

        # ---- MAKE_CHANGES / OUTPUT ----

        for username in sorted_leavable_users:
            self.namedrop_assignee(self.LEAVE, username)

        try:
            if self.strategy == "append":
                self.update_users(self.ADD, sorted_addable_users, issue["number"])

            elif self.strategy == "set":
                if not assigned_users:
                    self.update_users(self.ADD, sorted_addable_users, issue["number"])

            elif self.strategy == "change":
                self.update_users(self.REMOVE, sorted_removable_users, issue["number"])
                self.update_users(self.ADD, sorted_addable_users, issue["number"])
        except RequestException as e:
            pass


        # ---- FALLBACK LABEL ----

        if not assignable_users and not assigned_users:
            if self.fallback_label:
                if self.fallback_label in issue_labels:
                    self.write_fallback(f"already has label \"{self.fallback_label}\"")
                else:
                    if not self.dry_run:
                        issue_labels.append(self.fallback_label)
                        try:
                            self.hubcom.set_issue_labels(issue, issue_labels)
                            self.write_fallback(f"added label \"{self.fallback_label}\"")
                        except:
                            pass
                    else:
                        self.write_fallback(f"added label \"{self.fallback_label}\"")


def validate_reposlug(ctx, param, slug: str):
    """
    A click validator that check if the reposlug is in owner/reponame format

    :param ctx: mandatory for click validators, not used otherwise
    :param param: mandatory for click validators, not used otherwise
    :param slug: the actual string obtained from the user
    :return: a tuple `(owner, reponame)`
    """
    parts = slug.split("/")
    if not (len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0):
        raise click.BadParameter("not in owner/repository format")
    return parts[0], parts[1]


def validate_file(ctx, param: click.core.Option, path: str):
    """
    Attempts to load the file provided with configparser

    :param ctx: mandatory for click validators, not used otherwise
    :param param: mandatory for click validators, not used otherwise
    :param path: actually it's a file obtained open(path, "r") or something along those lines.
    :return: configparser object
    """
    try:
        cp = configparser.ConfigParser()
        cp.optionxform = str
        cp.read_file(path)
    except FileNotFoundError:
        raise click.BadParameter("incorrect configuration format")
    if len(cp) < 2:
        raise click.BadParameter("incorrect configuration format")
    return cp


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

    # ---- SETUP ----

    ghia_solver = GHIASolver(config_auth, config_rules, reposlug, strategy, dry_run)
    ghia_solver.solve()
