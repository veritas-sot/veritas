import logging
import os
from pathlib import Path
from git import Repo, GitCommandError
from git.objects import Commit as GitCommit


class Repository:

    def __init__(self, path: str, repo: str, account=None, ssh_key=None):
            self.path = Path(path).expanduser().resolve()
            self._repo = repo
            if ssh_key:
                self._ssh_cmd = f'ssh -i {ssh_key}'
            else:
                self._ssh_cmd = None

            # Initialize repository
            logging.debug(f'opening REPO {path} / {self.path} / ssh {self._ssh_cmd}')
            self._open_repository()
            if account is not None and repo is not None:
                self._remote = f'https://github.com/{account}/{repo}.git'

    def _open_repository(self):
        self._repo = Repo(str(self.path))

    def clone(self, full_local_path):
        if self._ssh_cmd:
            with self._repo.git.custom_environment(GIT_SSH_COMMAND=self._ssh_cmd):
                return self._repo.clone_from(self._remote, full_local_path)
        return self._repo.clone_from(self._remote, full_local_path)

    def get_config(self):
        with self._repo.config_reader() as git_config:
            print(git_config.get_value('user', 'email'))
            print(git_config.get_value('user', 'name'))

    def has_changes(self):
        if self._repo.is_dirty(untracked_files=True):
            logging.debug('Changes detected')
            return True
        return False

    def get_diff(self):
        return self._repo.git.diff(self._repo.head.commit.tree)

    def add(self, files):
        self._repo.index.add(files)

    def add_all(self):
        self._repo.git.add('--all')

    def commit(self, comment=''):
        self._repo.index.commit(comment)

    def push(self):
        if self._ssh_cmd:
            with self._repo.git.custom_environment(GIT_SSH_COMMAND=self._ssh_cmd):
                return self._repo.remotes.origin.push(env={"GIT_SSH_COMMAND": self._ssh_cmd })
        return self._repo.remotes.origin.push()

    def pull(self):
        if self._ssh_cmd:
            with self._repo.git.custom_environment(GIT_SSH_COMMAND=self._ssh_cmd):
                return self._repo.remotes.origin.pull(env={"GIT_SSH_COMMAND": self._ssh_cmd })
        return self._repo.remotes.origin.pull()

    def remotes(self):
        return self._repo.remotes

    def commits(self, number_of_commits=5):
        return list(self._repo.iter_commits('main'))[:number_of_commits]

    def branch(self):
        return self._repo.active_branch.name

    def branches(self):
        return self._repo.branches

    def get(self, filename):
        # check if path exists
        local_path = Path("%s/%s" % (self.path, filename))
        if local_path.is_file():
            return local_path.read_text()
        else:
            logging.error(f'file {local_path} does not exists')
            return None

    def write(self, filename, content):
        local_path = Path("%s/%s" % (self.path, filename))
        try:
            with open(local_path, "w") as filehandler:
                filehandler.write(content)
                filehandler.close()
                return True
        except Exception as exc:
            logging.error(f'could not write {local_path}; got exception {exc}')
            return False

        return False