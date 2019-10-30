import re

import click
import requests


class RequestException(Exception):
    pass


class GithubCommunicator:

    def __init__(self, token, owner, repo):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Python', 'Authorization': f'token {token}'}

        self.owner = owner
        self.repo = repo

    def get_user_info(self):
        r = self.session.get('https://api.github.com/user')
        return r.json()

    def get_issue_list(self):
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

    def update_assignee(self, action, username, issue_number):
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

    def set_issue_labels(self, issue, issue_labels):
        r = self.session.post(
            f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{issue['number']}/labels",
            json={"labels": issue_labels})
        if r.status_code != 200:
            self.write_error(f"Could not update issue {self.owner}/{self.repo}#{issue['number']}", 3)
            raise RequestException("boo2")

    # ----Utility----

    def get_next_page_link_from_request(self, request):
        next_page_regexp = re.compile("<([^>]*)>; rel=\"next\"")

        next_page_match = None
        if "Link" in request.headers:
            next_page_match = next_page_regexp.search(request.headers["Link"])

        if next_page_match is not None:
            return next_page_match.group(1)
        return None

    def write_error(self, message: str, indentation=0):
        click.secho(indentation * " " + "ERROR: ", bold=True, nl=False, fg="red", err=True)
        click.secho(message, err=True)