#!/usr/bin/python2.7

import csv
import datetime
import github
import urllib2
import time
import os

SUGGESTION = "```suggestion\r\n"
CODE = "```"


def _get_code(comment):
    start = comment.index(SUGGESTION) + len(SUGGESTION)
    try:
        end = comment.index(CODE, start)
    except ValueError:
        end = len(comment)
    return comment[start:end].replace("\n", "").replace("\r", "").lstrip(" ")


def _wget(link):
    try:
        src = urllib2.urlopen(link).read()
    except urllib2.HTTPError:
        print("ERROR: ", link)
        return ""
    return src

def is_applied(pull, comment):
    # Check if the suggested code exists in the latest version
    code = _get_code(comment.body)
    if pull.commits > 1:
        for commit in pull.get_commits():
            if (
                comment.path in [f.filename for f in commit.files]
                and commit.commit.committer.date > comment.created_at
            ):
                file_url = (
                    commit.html_url.replace(
                        "github.com", "raw.githubusercontent.com"
                    ).replace("commit/", "")
                    + "/"
                    + comment.path
                )
                src = _wget(file_url)
                if any(
                    [
                        line.replace("\n", "").lstrip(" ") == code
                        for line in src.split("\n")
                    ]
                ):
                    return commit
    return None

def is_suggestion(comment):
    # Check if comment contains code suggestion to user
    if SUGGESTION in comment:
        return True
    return False

def check_issues(issue):
    # Collect data for issues without pull requests
    time.sleep(5)
    row = [
        issue.repository.full_name.encode('utf-8'),
        issue.number,
        issue.user.login.encode('utf-8'),
        issue.closed_by.login.encode('utf-8') if issue.closed_by else "",
        issue.state.encode('utf-8'),
        str((issue.closed_at - issue.created_at).total_seconds())
        if issue.closed_at
        else "",
        ";".join([i.name for i in issue.labels]).encode('utf-8'),
    ]
    if issue.state == "closed":
        with open("issAccepted.csv", "a") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(row)
    else:
        with open("issRejected.csv", "a") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(row)


def check_pulls(pull, sugg):
    # Collect data from pull requests with no code suggestions
    time.sleep(5)
    row = [
        pull.base.repo.full_name.encode('utf-8'),
        pull.number,
        pull.user.login.encode('utf-8'),
        pull.merged_by.login.encode('utf-8') if pull.merged_by else "",
        pull.merged,
        pull.state.encode('utf-8'),
        str((pull.closed_at - pull.created_at).total_seconds())
        if pull.closed_at
        else "",
        str((pull.merged_at - pull.created_at).total_seconds())
        if pull.merged_at
        else "",
        sugg,
        pull.changed_files,
        ";".join([f.filename for f in pull.get_files()]).encode('utf-8'),
    ]
    if pull.merged is True:
        with open("pullsAccepted.csv", "a") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(row)
    else:
        with open("pullsRejected.csv", "a") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(row)


def check_comments(pull):
    # Parse PR comments to search for code suggestions made by developers
    comments = pull.get_comments()
    sugg = False
    for c in comments:
        time.sleep(5)
        row = [
            pull.base.repo.full_name.encode('utf-8'),
            pull.number,
            c.commit_id.encode('utf-8'),
            pull.user.login.encode('utf-8'),
            c.user.login.encode('utf-8'),
            pull.merged_by.login.encode('utf-8') if pull.merged_by else "",
            pull.merged,
            pull.state.encode('utf-8'),
            str((pull.merged_at - pull.created_at).total_seconds())
            if pull.merged_at
            else "",
            c.path.encode('utf-8'),
            repr(c.body),
        ]
        if is_suggestion(c.body):
            sugg = True
            applied = is_applied(pull, c)
            if applied is not None:
                row[9] = str(
                    (applied.commit.committer.date - c.created_at).total_seconds()
                )
                with open("accepted.csv", "a") as f:
                    writer = csv.writer(f, delimiter=",")
                    writer.writerow(row)
                print(row)
            else:
                with open("rejected.csv", "a") as f:
                    writer = csv.writer(f, delimiter=",")
                    writer.writerow(row)
                print(row)
    check_pulls(pull, sugg)


def _setup():
    # Create .csv files for storing data
    pull_header = [
        "repo",
        "pullID",
        "dev_user",
        "review_user",
        "merged",
        "state",
        "resolve_time",
        "accept_time",
        "suggested_change",
        "changed_files",
        "files",
    ]
    with open("pullsAccepted.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(pull_header)
    with open("pullsRejected.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(pull_header)
    code_header = [
        "repo",
        "pullID",
        "commitID",
        "dev_user",
        "sugg_user",
        "review_user",
        "merged",
        "state",
        "resolve_time",
        "accept_time",
        "files",
        "comment",
    ]
    with open("accepted.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(code_header)
    with open("rejected.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(code_header)
    issue_header = [
        "repo",
        "issueID",
        "dev_user",
        "review_user",
        "state",
        "resolve_time",
        "labels",
    ]
    with open("issAccepted.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(issue_header)
    with open("issRejected.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(issue_header)


def main():
    _setup()
    git = github.Github(os.environ['GITHUBTOKEN'])
    repos = git.search_repositories("q", sort="forks")
    d = datetime.datetime(2018, 10, 1)
    reps = 0
    prs = 0
    comments = 0
    iss = 0
    for repo in repos:
        reps += 1
        issues = repo.get_issues(state="all")
        for issue in issues:  # Pull requests are issues
            if d < issue.updated_at:
                if issue.pull_request is None:  # Issues
                    time.sleep(15)
                    iss += 1
                    check_issues(issue)
                else:  # Pull requests
                    pull = issue.as_pull_request()
                    time.sleep(15)
                    comments += pull.get_comments().totalCount
                    prs += 1
                    check_comments(pull)
                print(repo.full_name, issue.number, reps, prs, comments, iss)
            else:
                time.sleep(30)
                break


if __name__ == "__main__":
    main()
   