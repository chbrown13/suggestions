#!/usr/bin/python2.7

import csv
import datetime
import github
import urllib2
import time
import smtplib
import sys

SUGGESTION = "```suggestion\r\n"
CODE = "```"
SUGGESTEE = "Hi {user}! We noticed you recently received a comment using the new suggested changes feature on a review for a pull request you submitted to the {repo} repository on GitHub ({link}). Please consider filling out the brief survey below to provide feedback on your experience with this new feature. Your responses will be anonymized and used for research purposes, and completing the survey will give you the chance to win a $100 Amazon gift card! Thanks for your time.\n"
SUGGESTER = "Hi {user}! We noticed you recently used the new suggested changes feature to review a pull request for the {repo} repository on GitHub ({link}). Please consider filling out the brief survey below to provide feedback on your experience with this new feature. Your responses will be anonymized and used for research purposes, and completing the survey will give you the chance to win a $100 Amazon gift card! Thanks for your time.\n"

def is_suggestion(comment):
    # Check if comment contains code suggestion to user
    if SUGGESTION in comment:
        return True
    return False

def create_email(pull, comment):
    email1 = email2 = ''
    puller = pull.user
    commenter = comment.user
    if puller.email is not None:
        email1 = SUGGESTEE.replace('{user}', puller.login).replace('{repo}', pull.base.repo.name).replace('{link}', pull.html_url)
        with open('email.txt', 'a') as f:
            f.write("Suggestee: {email}\n".replace('{email}',puller.email))
            f.write(email1)
    if commenter.email is not None:
        email2 = SUGGESTER.replace('{user}', commenter.login).replace('{repo}', pull.base.repo.name).replace('{link}', pull.html_url)
        with open('email.txt', 'a') as f:
            f.write("Suggester: {email}\n".replace('{email}', commenter.email))
            f.write(email2)

def check_comments(pull):
    comments = pull.get_comments()
    arr = []
    for c in comments:
        if is_suggestion(c.body):
            print c.body.encode('utf-8')
            arr.append(c)
    return arr

def _get_code(comment):
    if is_suggestion(comment):
        delim = SUGGESTION
    else:
        return None
    start = comment.index(delim) + len(delim)
    end = comment.index("```", start)
    return comment[start:end].replace('\n','').replace('\r','').lstrip(' ')

def main():
    git = github.Github("{auth_token}")
    issues = git.search_issues("q={S} in:comments".replace('{S}',SUGGESTION), sort="updated")
    for issue in issues:
        if issue.pull_request is not None:
            comments= check_comments(issue.as_pull_request())
            for comment in comments:
                create_email(issue.as_pull_request(), comment)
                with open('email.txt', 'a') as f:
                    try:
                        f.write(comment.body.decode('utf-8').strip() + '\n' + issue.html_url + '\n')
                    except UnicodeEncodeError:
                        f.write('ERROR: ' + issue.html_url + '\n')
                        continue
                # with open('sample.txt', 'a') as f:
                #     try:
                #         f.write(issue.html_url + ' ' + comment.html_url + '   ' + _get_code(comment.body) + '\n')
                #     except UnicodeEncodeError:
                #         f.write('ERROR: ' + issue.html_url + '\n')
                #         continue


if __name__ == "__main__":
    main()
