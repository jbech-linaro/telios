from git import Repo
from git import RemoteProgress
import logging
import pathlib
import shutil

import src

class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(message or "", end='\r')

def show(args):
    print("show")


def create_remote(repository, remote_name, remote_url):
    remote = repository.create_remote(remote_name, url=remote_url)
    assert remote.exists()


def clone_git(src, dest, commit, upstream_url):
    logging.debug(f"src: {src}")
    logging.debug(f"dest: {dest}")
    logging.debug(f"commit: {commit}")
    logging.debug(f"upstream_url: {upstream_url}")
    print(f"[+] {src} --> {dest}")
    repository = Repo.clone_from(src, dest, no_checkout=True,
                                 progress=CloneProgress())
    repository.git.checkout(commit)
    # Make an upstream remote for convenience
    create_remote(repository, "upstream", upstream_url)


def create_mirror(src, dest, name):
    logging.debug(f"Cloning mirror: {name}")
    print(f"[+] {src} --> {dest}")
    repository = Repo.clone_from(src, dest, no_checkout=True,
                                 progress=CloneProgress())
    return repository


def update_git(dest, name):
    print(f"[u] {name} : {dest}")
    repository = Repo(dest)
    repository.git.remote('update')


def wipe_path(dest):
    path = pathlib.Path(dest)
    if path.exists():
        print(f"[-] {dest}")
        shutil.rmtree(path)


def clone(args, workdir):
    logging.debug(f"file {args.file}")
    yml = src.load_yml(args.file)
    nbr_gits = len(yml['gits'])
    if nbr_gits < 1:
        return

    # Todo:
    # - Use several threads
    # - Use partial clone
    print(f"{nbr_gits} gits found in {args.file} ...")
    for g in yml['gits']:
        git_name = g['name']
        git_url = g['url']
        git_commit = g['commit']

        logging.debug(g)
        source = git_url
        dest = f"{workdir}/{git_name}"

        if yml.get('mirror', None) is not None:
            source = f"{yml['mirror']}/{git_name}"

            if args.wipe_mirrors:
                wipe_path(source)

            path = pathlib.Path(source)
            if path.exists():
                if args.update:
                    update_git(source, git_name)
            else:
                repository = create_mirror(git_url, source, git_name)
                repository.git.checkout(git_commit)

        if args.wipe:
            wipe_path(dest)

        path = pathlib.Path(dest)
        if path.exists():
            if args.update:
                update_git(dest, git_name)
        else:
            clone_git(source, dest, git_commit, git_url)


def clone_main(args, workdir):
    global comments

    if args.show:
        show(args)
    if args.file:
        clone(args, workdir)

    comments = None
