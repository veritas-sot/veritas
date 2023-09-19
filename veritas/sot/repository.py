import logging
import os
import datetime
from pathlib import Path
from pydriller import Repository as pyRepository
from git import Repo, GitCommandError
from git.objects import Commit as GitCommit

#
# todo
#
# git log -p -- path/to/file
# git diff HEAD^^

class Repository:

    def __init__(self, path: str, repo: str):
            self.path = Path(path).expanduser().resolve()
            self._repo_name = repo
            # Initialize repository
            logging.debug(f'opening REPO {path} / {self.path} / ssh {self._ssh_cmd}')
            self._open_repository()

    def __getattr__(self, item):
        if item == 'remotes':
            return self._repo.remotes

    def _open_repository(self):
        self._repo = Repo(str(self.path))

    def get_repo(self):
        return self._repo

    def get_index(self):
        return self._repo.index

    def get_config(self):
        config = {}
        with self._repo.config_reader() as git_config:
            config['user.email'] = git_config.get_value('user', 'email')
            config['user.name'] = git_config.get_value('user', 'name')

        return config

    def get_info(self):
        info = {}
        master = self._repo.head.reference
        lc = datetime.datetime.fromtimestamp(master.commit.committed_date)
        last_commit = lc.strftime("%Y_%m_%d_%H%M%S")
        info['current_branch'] = master.name
        info['last_commit'] = last_commit
        info['last_commit_id'] = master.commit.hexsha
        info['last_commit_by'] = master.commit.author.name
        info['last_commit_message'] = master.commit.message

        return info

    def get_last_commits(self, max_count, filename):
        commits_for_file_generator = self._repo.iter_commits(all=True, 
                                                             max_count=max_count, 
                                                             paths=filename)
        return [c for c in commits_for_file_generator]

    def get_last_commits_of(self, path):
        return [commit for commit in self._repo.iter_commits(paths=path)]

    def get_revision(self, path):
        # for commit, filecontents in revlist:
        #   ...
        return (
            (commit, (commit.tree / path).data_stream.read()) for commit in self._repo.iter_commits(paths=path)
        )

    def get_commits(self):

        commits = []
        for commit in pyRepository(str(self.path)).traverse_commits():

            hash = commit.hash

            # Gather a list of files modified in the commit
            files = []
            try:
                for f in commit.modified_files:
                    if f.new_path is not None:
                        files.append(f.new_path) 
            except Exception:
                print('Could not read files for commit ' + hash)
                continue

            # Capture information about the commit in object format so I can reference it later
            record = {
                'hash': hash,
                'message': commit.msg,
                'author_name': commit.author.name,
                'author_email': commit.author.email,
                'author_date': str(commit.author_date),
                'author_tz': commit.author_timezone,
                'committer_name': commit.committer.name,
                'committer_email': commit.committer.email,
                'committer_date': str(commit.committer_date),
                'committer_tz': commit.committer_timezone,
                'in_main': commit.in_main_branch,
                'is_merge': commit.merge,
                'num_deletes': commit.deletions,
                'num_inserts': commit.insertions,
                'net_lines': commit.insertions - commit.deletions,
                'num_files': commit.files,
                'branches': ', '.join(commit.branches), # Comma separated list of branches the commit is found in
                'files': ', '.join(files), # Comma separated list of files the commit modifies
                'parents': ', '.join(commit.parents), # Comma separated list of parents
                # PyDriller Open Source Delta Maintainability Model (OS-DMM) stat. See https://pydriller.readthedocs.io/en/latest/deltamaintainability.html for metric definitions
                'dmm_unit_size': commit.dmm_unit_size,
                'dmm_unit_complexity': commit.dmm_unit_complexity,
                'dmm_unit_interfacing': commit.dmm_unit_interfacing,
            }
            # Omitted: modified_files (list), project_path, project_name
            commits.append(record)
        return commits

    def get_commits_details(self, diff=False, diff_parsed=False, source=False, source_before=False):
        commits = []

        for commit in pyRepository(str(self.path)).traverse_commits():
            hash = commit.hash
            try:
                for f in commit.modified_files:
                    record = {
                        'hash': hash,
                        'message': commit.msg,
                        'author_name': commit.author.name,
                        'author_email': commit.author.email,
                        'author_date': str(commit.author_date),
                        'author_tz': commit.author_timezone,
                        'committer_name': commit.committer.name,
                        'committer_email': commit.committer.email,
                        'committer_date': str(commit.committer_date),
                        'committer_tz': commit.committer_timezone,
                        'in_main': commit.in_main_branch,
                        'is_merge': commit.merge,
                        'num_deletes': commit.deletions,
                        'num_inserts': commit.insertions,
                        'net_lines': commit.insertions - commit.deletions,
                        'num_files': commit.files,
                        'branches': ', '.join(commit.branches),
                        'filename': f.filename,
                        'old_path': f.old_path,
                        'new_path': f.new_path,
                        'nloc': f.nloc,
                        'added_lines': f.added_lines,
                        'deleted_lines': f.deleted_lines,
                        'project_name': commit.project_name,
                        'project_path': commit.project_path, 
                        'parents': ', '.join(commit.parents),
                    }
                    if diff:
                        record.update({'diff': f.diff})
                    if diff_parsed:
                        record.update({'diff_parsed': f.diff_parsed})
                    if source:
                        record.update({'source_code': f.source_code})
                    if source_before:
                        record.update({'source_code_before': f.source_code_before})
                    commits.append(record)
            except Exception:
                print('Problem reading commit ' + hash)
                continue 
        return commits

    def set_config(self, key, sub_ey, value):
        # user.name = value
        with self._repo.config_writer() as config:
            config.set_value(key, sub_key, value)

    def create_remote(self, remote_name, url):
        self._repo.create_remote(remote_name, url)

    def has_changes(self):
        if self._repo.is_dirty(untracked_files=True):
            logging.debug('Changes detected')
            return True
        return False

    def get_untracked_files(self):
        return self._repo.untracked_files

    def get_diff_summary(self, name_only=True):
        return self._repo.git.diff('HEAD~1..HEAD', name_only=name_only)

    def get_diff(self):
        return self._repo.head.commit

    def add(self, files):
        self._repo.index.add(files)

    def add_all(self):
        self._repo.git.add(all=True)

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

    def commits(self, number_of_commits=5):
        return list(self._repo.iter_commits('main'))[:number_of_commits]

    def branch(self):
        return self._repo.active_branch.name

    def get_branch(self):
        return self._repo.head.reference

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