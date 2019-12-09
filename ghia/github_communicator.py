import re


import click
import requests
from typing import List

class RequestException(Exception):
    pass

"""
This class is responsible for communicating with github
"""
class GithubCommunicator:

    def __init__(self, token: str, owner: str, repo: str):
        """
        Initialize the object and its session

        :param token: an API token used by GitHub
        :param owner: the username of the repo owner
        :param repo: name of the repository, usually it's at the end of the repo url in a owner/repo format
        """
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Python', 'Authorization': f'token {token}'}

        self.owner = owner
        self.repo = repo

    def get_user_info(self):
        """
        Asks github about info on the user authenticated ba the api key

        :return: json received after asking github about the logged-in user
        """
        r = self.session.get('https://api.github.com/user')
        return r.json()

    def get_issue_list(self):
        """
        Collects json of all open issues into a list
Git
        :return: List of json issues
        """
        issue_list = []
        r = self.session.get(f"https://api.github.com/repos/{self.owner}/{self.repo}/issues")
        if r.status_code != 200:
            self.write_error(f"Could not list issues for repository {self.owner}/{self.repo}")
            raise RequestException("boo")
        else:
            issue_list.extend(r.json())
            next_page_url = self.get_next_page_link_from_request(r)
            while next_page_url is not None:
                r = self.session.get(next_page_url)
                issue_list.extend(r.json())
                next_page_url = self.get_next_page_link_from_request(r)
        return issue_list

    def update_assignee(self, action: int, username: str, issue_number):
        """
        Tells github to add or remove an assignee on an issue

        :param action: a number, 0 means ADD, 1 means REMOVE, getting the enumeration into a separate file for use in here is harder than writing this
        :param username: username to assign or delete
        :param issue_number: number of the issue that is in need of changing
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{issue_number}/assignees"
        if action == 0:
            r = self.session.post(url, json={"assignees": [username]})
            if r.status_code != 201:
                self.write_error(f"Could not update issue {self.owner}/{self.repo}#{issue_number}", 3)
                raise RequestException("boo2")
        elif action == 1:
            r = self.session.delete(url, json={"assignees": [username]})
            if r.status_code != 200:
                self.write_error(f"Could not update issue {self.owner}/{self.repo}#{issue_number}", 3)
                raise RequestException("boo2")

    def set_issue_labels(self, issue, issue_labels: List[str]):
        """
        Politely asks github to add labels in a list

        :param issue: the issue json that should be labeled
        :param issue_labels: Which labels should be put on it
        """
        r = self.session.post(
            f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{issue['number']}/labels",
            json={"labels": issue_labels})
        if r.status_code != 200:
            self.write_error(f"Could not update issue {self.owner}/{self.repo}#{issue['number']}", 3)
            raise RequestException("boo2")

    # ----Utility----

    def get_next_page_link_from_request(self, request):
        """
        Handles inconveniences when getting a link to the next page in a function, so it doesn't stink everywhere
        needs the header to be in a special format expected to be returned from github when asked nicely

        :param request: a request that is actually a response, oops, not changing that now, also it is expected to contain a link to the next page in its header
        :return: The link if there is one, otherwise None is returned
        """
        next_page_regexp = re.compile("<([^>]*)>; rel=\"next\"")

        next_page_match = None
        if "Link" in request.headers:
            next_page_match = next_page_regexp.search(request.headers["Link"])

        if next_page_match is not None:
            return next_page_match.group(1)
        return None

    def write_error(self, message: str, indentation=0):
        """
        Writes an indented error because that was the requirement. Guys, the app just failed, but the error is indented so no need to panic...
        Am i bored? No, why would i be bored?

        :param message: le message to be printed
        :param indentation: a number of spaces that will be added in front
        """
        click.secho(indentation * " " + "ERROR: ", bold=True, nl=False, fg="red", err=True)
        click.secho(message, err=True)