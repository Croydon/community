from github import Github

import os

g = Github(os.getenv("GITHUB_TOKEN"))


print(os.getenv("GITHUB_EVENT_NAME"))
print(os.getenv("GITHUB_EVENT_PATH"))
print(os.getenv("GITHUB_REF"))
print(os.getenv("GITHUB_SHA"))

with open(os.getenv("GITHUB_EVENT_PATH"), mode="r") as payload:
    print(payload.read())
