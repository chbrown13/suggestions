#!/usr/bin/python2.7

import csv
import datetime
import github
import urllib2
import time

SUGGESTION = "```suggestion\r\n"
CODE = "```"

def _get_code(comment):
    if is_suggestion(comment):
        delim = SUGGESTION
    else:
        return None
    start = comment.index(delim) + len(delim)
    end = comment.index("```", start)
    return comment[start:end].replace('\n','').replace('\r','').lstrip(' ')

def is_applied(pull, comment):
    code = _get_code(comment.body)
    if pull.commits > 1 or code is None:
        for commit in pull.get_commits():
            if comment.path in [f.filename for f in commit.files]:
                file_url = commit.html_url.replace("github.com","raw.githubusercontent.com").replace("commit/", "") + "/" + comment.path
                try:
                    src = urllib2.urlopen(file_url).read()
                except urllib2.HTTPError:
                    print('ERROR: ', file_url)
                    return False
                if any([line.replace('\n','').lstrip(' ') == code for line in src.split('\n')]):
                    return True
    return False

def is_suggestion(comment):
    # Check if comment contains code suggestion to user
    if SUGGESTION in comment:
        return True
    return False
    
def check_comments(pull):
    # Parse PR comments to look for GitHub code suggestions by developers
    comments = pull.get_comments()
    for c in comments:
        time.sleep(5)
        row = [str(pull.base.repo.full_name), str(pull.number), str(c.commit_id), str(pull.user.login), \
            str(pull.user.email), str(c.user.login), str(c.user.email), repr(c.body), str(is_applied(pull,c)), str(pull.base.repo.language)]
        if is_suggestion(c.body):
            if is_applied(pull, c):
                with open('suggAccept.csv', 'a') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerow(row)
                print(row)
            else:
                with open('suggReject.csv', 'a') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerow(row)
                print(row)

def _setup():
    header = ["repo","pullID","commitID","dev_user","dev_email","review_user","review_email","comment","applied","language"]
    with open('sugg1.csv', 'w') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(header)
    with open('sugg2.csv', 'w') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(header)


_setup()
git = github.Github("{auth_token}")
repos = git.search_repositories('q', sort='forks')
d = datetime.datetime(2018, 10, 1)
reps = 0
pr = 0
comments = 0
for repo in repos:
    reps += 1
    for pull in repo.get_pulls('all'):
        time.sleep(20)
        pr += 1
        comments += pull.comments
        if d < pull.updated_at:
            print(repo.html_url, pull.number, reps, pr, comments)
            try:
                check_comments(pull)
            except github.GithubException:
                time.sleep(3600)
                check_comments(pull)
        else:
            break
    time.sleep(100)
