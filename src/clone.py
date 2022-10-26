from git import Repo
import logging
import pathlib
import shutil

import src

def show(args):
    print("show")

def clone_git(src, dest, commit, upstream_url):
    logging.debug(f"src: {src}")
    logging.debug(f"dest: {dest}")
    logging.debug(f"commit: {commit}")
    logging.debug(f"upstream_url: {upstream_url}")
    repository = Repo.clone_from(src, dest, no_checkout=True)
    repository.git.checkout(commit)
    # Make an upstream remote for convenience
    create_remote(repository, "upstream", upstream_url)


def create_remote(repository, remote_name, remote_url):
    remote = repository.create_remote(remote_name, url=remote_url)


def create_mirror(url, dest, name):
    logging.debug(f"Cloning mirror: {name}")
    repository = Repo.clone_from(url, dest, no_checkout=True)
    return repository


def update_mirror(dest, name):
    logging.debug(f"Updating mirror: {name}")
    repository = Repo(dest)
    repository.remotes.origin.fetch()


def wipe_path(dest):
    path = pathlib.Path(dest)
    if path.exists():
        logging.debug(f"Removing: {dest}")
        shutil.rmtree(path)


def clone(args, workdir):
    logging.debug(f"file {args.file}")
    yml = src.load_yml(args.file)
    nbr_gits = len(yml['gits'])
    if nbr_gits < 1:
        return

    # Todo:
    # - Update if already cloned
    # - Add progress bar (https://stackoverflow.com/questions/2472552/python-way-to-clone-a-git-repository)
    # - Use several threads
    # - Use partial clone
    print(f"Start cloning {nbr_gits} ...")
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
                update_mirror(source, git_name)
            else:
                repository = create_mirror(git_url, source, git_name)
                repository.git.checkout(git_commit)

        if args.wipe:
            wipe_path(dest)

        clone_git(source, dest, git_commit, git_url)


def clone_main(args, workdir):
    global comments

    if args.show:
        show(args)
    if args.file:
        clone(args, workdir)

    comments = None
