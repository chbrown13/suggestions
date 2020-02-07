#!/usr/bin/python2.7

import csv
import datetime
import github
import urllib2
import time
import os

SUGGESTION = "```suggestion\r\n"
CODE = "```"


def _get_code(comment, delim):
    start = comment.index(delim) + len(delim)
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

def is_applied(pull, comment, kind):
    # Check if the suggested code exists in the latest version
    code = _get_code(comment.body, kind)
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
    # Check if pull request comment contains code suggestion to user
    if SUGGESTION in comment:
        return True
    return False

def is_code_comment(comment):
    # Check if a pull request comment contains markdown code suggested to user
    if SUGGESTION not in comment and CODE in comment:
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
        str(issue.comments),
        str((issue.closed_at - issue.created_at).total_seconds())
        if issue.closed_at
        else "",
        ";".join([i.name for i in issue.labels]).encode('utf-8'),
    ]
    with open("issues.csv", "a") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(row)


def check_pulls(pull, sugg, code):
    # Collect data from pull requests with no code suggestions
    time.sleep(5)
    row = [
        pull.base.repo.full_name.encode('utf-8'),
        pull.number,
        pull.user.login.encode('utf-8'),
        pull.merged_by.login.encode('utf-8') if pull.merged_by else "",
        pull.state.encode('utf-8'),
        pull.merged,
        str(sugg),
        str(code),
        str(pull.comments),
        str((pull.closed_at - pull.created_at).total_seconds())
        if pull.closed_at else "",
        str((pull.merged_at - pull.created_at).total_seconds())
        if pull.merged_at else ""
    ]
    with open("pull_requests.csv", "a") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(row)


def check_comments(pull):
    # Parse PR comments to search for code suggestions made by developers
    comments = pull.get_comments()
    sugg = 0
    code = 0
    for c in comments:
        time.sleep(5)
        row = [
            pull.base.repo.full_name.encode('utf-8'),
            pull.number,
            c.commit_id.encode('utf-8'),
            pull.user.login.encode('utf-8'),
            c.user.login.encode('utf-8'),
            pull.merged_by.login.encode('utf-8') if pull.merged_by else "",
            pull.state.encode('utf-8'),
            pull.merged,
            str((pull.closed_at - pull.created_at).total_seconds())
            if pull.closed_at else "",
            str((pull.merged_at - pull.created_at).total_seconds())
            if pull.merged_at else "",
            str((c.created_at - pull.created_at).total_seconds()),
            c.path,
            None,
            None,
            repr(c.body)
        ]
        if is_suggestion(c.body):
            row[12] = "suggestion"
            sugg += 1
            applied = is_applied(pull, c, SUGGESTION)
            if applied is not None:
                row[13] = str(
                    (applied.commit.committer.date - c.created_at).total_seconds()
                )
            with open("suggested_changes.csv", "a") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(row)
        else:
            if is_code_comment(c.body):
                row[12] = "code_comment"
                code += 1
                applied = is_applied(pull, c, CODE)
                if applied is not None:
                    row[13] = str(
                        (applied.commit.committer.date - c.created_at).total_seconds()
                    )
            else:
                row[12] = "comment"
            with open("comments.csv", "a") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(row)
        print(row)
    check_pulls(pull, sugg, code)


def _setup():
    # Create .csv files for storing data
    pull_header = [
        "repo",
        "number",
        "developer",
        "reviewer",
        "state",
        "merged",
        "num_suggestions",
        "num_code_comments",
        "num_comments",
        "resolve_time",
        "accept_time"
    ]
    with open("pull_requests.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(pull_header)
    sugg_header = [
        "repo",
        "pull_number",
        "commit",
        "developer",
        "suggester",
        "reviewer",
        "state",
        "merged",
        "pr_resolve_time",
        "pr_accept_time",
        "time_to_comment",
        "file",
        "type",
        "accept_time",
        "comment",
    ]
    with open("suggested_changes.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(sugg_header)
    with open("comments.csv", "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(sugg_header)
    issue_header = [
        "repo",
        "number",
        "user",
        "reviewer",
        "state",
        "resolve_time",
        "num_comments",
        "labels"
    ]
    with open("issues.csv", "w") as f:
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
   