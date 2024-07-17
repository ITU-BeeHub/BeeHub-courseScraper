import git
import os

def pushChanges(repo_path: os.PathLike, commit_message: str):
    
    # initialize the repository
    repo = git.Repo.init(repo_path)

    # add all files to the staging area
    repo.git.add(".")

    # commit the changes
    repo.index.commit(commit_message)

    # push the changes to the remote repository
    origin = repo.remote(name="origin")
    origin.push()

