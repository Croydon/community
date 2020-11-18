from github import Github

import os
import json
import subprocess
import pprint

REPOSITORY_SLUG = "Croydon/community"  # TODO env var
g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo(REPOSITORY_SLUG)

event_name = os.getenv("GITHUB_EVENT_NAME")
event_path = os.getenv("GITHUB_EVENT_PATH")
event_ref = os.getenv("GITHUB_REF")
event_sha = os.getenv("GITHUB_SHA")
print("event_name: {}".format(event_name))
print("event_path: {}".format(event_path))
print("event_ref: {}".format(event_ref))
print("event_sha: {}".format(event_sha))
print("")
print("")

def print_error(output_str: str):
    print(output_str)
    exit(1)

if event_name != "workflow_run" and event_name != "pull_request_review":
    print_error("Unexpected event_name which triggered this workflow run: {}".format(event_name))

event_data = {}
with open(os.getenv("GITHUB_EVENT_PATH"), mode="r") as payload:
    event_data = json.load(payload)
    # pprint.pprint(event_data)


pull_request_number = "0"
if event_name == "workflow_run":
    if len(event_data["workflow_run"]["pull_requests"]) != 1:
        print("This workflow_run is either connected to several pull requests or none. Nothing to merge.")
        exit(0)
    pull_request_number = event_data["workflow_run"]["pull_requests"][0]["number"]
elif event_name == "pull_request_review":
    pull_request_number = event_data["pull_request"]["number"]

print("pull_request_number: {}".format(pull_request_number))

if pull_request_number == "0":
    print_error("pull_request_number could not be detected in the event payload")

# workflow_run.pull_requests.number -> 1
# workflow_run.pull_requests.id -> 522534189
# workflow_run.pull_requests.url
# workflow_run.conclusion == "success"

# pull_request_review.author_association == "Collaborator" || "OWNER" ?
# pull_request.state == "approved" ? is dismissed a state we would get here?

pr = repo.get_pull(pull_request_number)

if not pr.mergeable:
    print("According to GitHub the pull request is not mergeable right now. Are there conflicts?")
    exit(0)

pr_latest_commit = pr.head.sha

print("latest commit in pull request: {}".format(pr_latest_commit))

reviews = pr.get_reviews()


print("all reviews on latest commit:")

print("")

changes_requested = False
approvals_on_latest_commit = 0
approvals_required = 1

latest_review_by_user = {}
for review in reviews:
    # TODO: Check if review comes from an OWNER or Collaborator
    latest_review_by_user[review.user.login] = review

for _, review in latest_review_by_user.items():
    # CHANGES_REQUESTED should be always dismissed or changed to an APPROVAL
    # Even if the CHANGES_REQUESTED do not happen on the latest commit,
    # they should be respected
    if review.state == "CHANGES_REQUESTED":
        changes_requested = True

    if review.commit_id == pr_latest_commit:
        print("{}: {} on commit: {}".format(review.user, review.state, review.commit_id))

        if review.state == "APPROVED":
            approvals_on_latest_commit = approvals_on_latest_commit + 1

print("")
print("")
print("approvals_on_latest_commit: {}".format(approvals_on_latest_commit))
print("approvals_required: {}".format(approvals_required))
print("")
print("")

if changes_requested:
    print("The pull request contains at least one request for changes. This has to be addressed first.")
    exit(0)

if approvals_on_latest_commit < approvals_required:
    print("The amount of required approvals are not reached yet.")
    exit(0)

print("Required approvals reached and no request for changes. Checking latest commit status...")
print("")

# There is a difference in commit statuses and checks
# Our CI runs are all qualifing as checks
# Since PyGithub is not yet supporting checks, we have to use something else here
# https://github.com/PyGithub/PyGithub/issues/1621
# TODO: Use only PyGithub one it supports checks

checks_api_call = subprocess.run(
    'curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/repos/{}/commits/{}/check-runs'.format(REPOSITORY_SLUG, pr_latest_commit),
    capture_output=True,
    shell=True
    )

checks_string = checks_api_call.stdout.decode("utf-8")

checks = json.loads(checks_string)


checks_successful = 0
# THIS workflow run (auto merge) is currently running, it can't be successful yet
# Therefore everything has to be successful except one
checks_successful_required = checks["total_count"] - 1

for check in checks["check_runs"]:
    if check["status"] == "completed" and check["conclusion"] == "success":
        checks_successful = checks_successful + 1
    elif check["status"] == "in_progress":
        if check["name"] != "Auto Merge Pull Requests":
            print("The check {} is still pending. Exiting.".format(check["name"]))
            exit(0)
    else:
            print("Unexpected status {} for check {}. Conclusion {}. Exiting.".format(check["status"], check["name"], check["conclusion"]))
            print(check)
            exit(0)

if checks_successful > checks_successful_required:
    print_error("More checks have passed as there should be. Something is wrong in our merge logic. Exiting.")

if checks_successful < checks_successful_required:
    print("Not all checks have passed. More work required 🙂")
    exit(0)

print("")
print("All checks passed. Merging...")

pr.merge(merge_method="squash")
