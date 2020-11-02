from appdirs import AppDirs
import os

from atlassian import Bitbucket

from dotenv import load_dotenv

from git import Repo
from git.exc import GitCommandError
from git.exc import NoSuchPathError

from requests.exceptions import HTTPError

load_dotenv()

BITBUCKET_URL = os.getenv("BITBUCKET_URL")
MERGING_SEQUENCE = os.getenv("MERGING_SEQUENCE").split(",")
PERSONAL_ACCESS_TOKEN = os.getenv("PERSONAL_ACCESS_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")
REPOSITORY_SLUG = os.getenv("REPOSITORY_SLUG")
REVIEWERS = os.getenv("REVIEWERS").split(",")
USERNAME = os.getenv("USERNAME")

ALREADY_UP_TO_DATE_MSG = "Already up to date."

bitbucket = Bitbucket(
    url=BITBUCKET_URL, username=USERNAME, password=PERSONAL_ACCESS_TOKEN
)

dirs = AppDirs("bitbucket-automator")


def can_merge_without_conflicts(source: str, destination: str) -> bool:
    local_repo_dir = os.path.join(dirs.user_cache_dir, PROJECT_KEY, REPOSITORY_SLUG)

    try:
        local_repo = Repo(local_repo_dir)
    except NoSuchPathError:
        repo_data = bitbucket.get_repo(PROJECT_KEY, REPOSITORY_SLUG)
        link = next(
            link for link in repo_data["links"]["clone"] if link["name"] == "ssh"
        )
        url = link["href"]
        local_repo = Repo.clone_from(url, local_repo_dir)

    local_repo.git.reset("--hard")
    local_repo.remote().fetch("--prune")
    local_repo.git.checkout(f"origin/{destination}")

    try:
        merge_output = local_repo.git.merge(f"origin/{source}")
    except GitCommandError as e:
        print(e.stdout.strip())
        return False
    else:
        print(merge_output)
        return ALREADY_UP_TO_DATE_MSG not in merge_output


def submit_pull_request(source: str, destination: str):
    title = f"Merge {source} to {destination}"
    pull_request = bitbucket.open_pull_request(
        PROJECT_KEY,
        REPOSITORY_SLUG,
        PROJECT_KEY,
        REPOSITORY_SLUG,
        source,
        destination,
        title,
        None,
        REVIEWERS,
    )
    print("Submitted")


def merge(pull_request):
    if any(
        reviewer["user"]["name"] == USERNAME and not reviewer["approved"]
        for reviewer in pull_request["reviewers"]
    ):
        bitbucket.change_reviewed_status(
            PROJECT_KEY, REPOSITORY_SLUG, pull_request["id"], "APPROVED", USERNAME
        )
        print("Approved")

    try:
        bitbucket.merge_pull_request(
            PROJECT_KEY, REPOSITORY_SLUG, pull_request["id"], pull_request["version"]
        )
    except HTTPError as e:
        for error in e.response.json()["errors"]:
            for veto in error["vetoes"]:
                print(veto["summaryMessage"])
    else:
        print("Merged")


def main():
    open_pull_requests = bitbucket.get_pull_requests(PROJECT_KEY, REPOSITORY_SLUG)

    for source, destination in zip(MERGING_SEQUENCE[:-1], MERGING_SEQUENCE[1:]):
        print(f"{source} -> {destination}")

        try:
            matching_pull_request = next(
                pr
                for pr in open_pull_requests
                if pr["fromRef"]["id"] == f"refs/heads/{source}"
                and pr["toRef"]["id"] == f"refs/heads/{destination}"
            )
        except StopIteration:
            if can_merge_without_conflicts(source, destination):
                submit_pull_request(source, destination)
        else:
            merge(matching_pull_request)


if __name__ == "__main__":
    main()
