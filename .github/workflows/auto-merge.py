from github import Github

import os
import json
import pprint

g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo("Croydon/community") # TODO env var

event_name = os.getenv("GITHUB_EVENT_NAME")
event_path = os.getenv("GITHUB_EVENT_PATH")
event_ref = os.getenv("GITHUB_REF")
event_sha = os.getenv("GITHUB_SHA")
print(event_name)
print(event_path)
print(event_ref)
print(event_sha)

def print_error(output_str: str):
    print(output_str)
    exit(1)

if event_name != "workflow_run" and event_name != "pull_request_review":
    print_error("Unexpected event_name which triggered this workflow run: {}".format(event_name))

event_data = {}
with open(os.getenv("GITHUB_EVENT_PATH"), mode="r") as payload:
    event_data = json.load(payload)
    pprint.pprint(event_data)


pull_request_number = "0"
if event_name == "workflow_run":
    pull_request_number = event_data["pull_requests"]["number"]
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

pprint.pprint(latest_review_by_user)

for _, review in latest_review_by_user.items():
    # CHANGES_REQUESTED should be always dismissed or changed to an APPROVAL
    # Even if the CHANGES_REQUESTED do not happen on the latest commit,
    # they should be respected
    if review.state == "CHANGES_REQUESTED":
        changes_requested = True

    if review.commit_id == pr_latest_commit:
        print("{}: {} on commit: {}".format(review.user, review.state, review.commit_id))

        if review.state == "APPROVAL":
            approvals_on_latest_commit = approvals_on_latest_commit + 1

print("")
print("")
print("approvals_on_latest_commit: {}".format(approvals_on_latest_commit))
print("approvals_required: {}".format(approvals_required))
print("")
print("")

if changes_requested:
    print("The pull request contains at least one request for changes on the latest commit. This has to be addressed first.")
    exit(0)

if approvals_on_latest_commit < approvals_required:
    print("The amount of required approvals are not reached yet.")
    exit(0)

print("Required approvals reached and no request for changes. Checking latest commit status...")
# TODO
