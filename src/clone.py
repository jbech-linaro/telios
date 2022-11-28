from concurrent.futures import ThreadPoolExecutor, as_completed
from git import Repo
from git import RemoteProgress
from multiprocessing import Pool, TimeoutError
from random import randrange
from threading import Thread, active_count
from time import sleep, time
import logging
import pathlib
import shutil

import src

class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(message or "", end='\r')

def show(args):
    print("show")


def timer(func):
    def wrapper(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f"{func.__name__} completed in {(t2-t1):0.2f}s")
    return wrapper


def create_remote(repository, remote_name, remote_url):
    remote = repository.create_remote(remote_name, url=remote_url)
    assert remote.exists()


def clone_git(src, dest, commit, upstream_url, reference=False):
    logging.debug(f"src: {src}")
    logging.debug(f"dest: {dest}")
    logging.debug(f"commit: {commit}")
    logging.debug(f"upstream_url: {upstream_url}")
    if reference:
        print(f"[+r] {src} --> {dest}")
        repository = Repo.clone_from(upstream_url, dest, no_checkout=True,
                                     progress=CloneProgress(), reference=src)
    else:
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


@timer
def clone_single(args, workdir, mirror, git_data):
    git_name = git_data['name']
    git_url = git_data['url']
    git_commit = git_data['commit']

    source = git_url
    dest = f"{workdir}/{git_name}"

    if mirror:
        source = f"{mirror}/{git_name}"

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
        if args.reference:
            clone_git(source, dest, git_commit, git_url, reference=True)
        else:
            clone_git(source, dest, git_commit, git_url)


def clone(args, workdir):
    logging.debug(f"file {args.file}")
    yml = src.load_yml(args.file)
    nbr_gits = len(yml['gits'])
    if nbr_gits < 1:
        return

    print(f"{nbr_gits} gits found in {args.file} ...")

    mirror = yml.get('mirror', None)

    with ThreadPoolExecutor(args.jobs) as executor:
        for git_data in yml['gits']:
            _ = executor.submit(clone_single, args, workdir, mirror, git_data)
            #try:
            #    result = future.result()
            #except:
            #    logging.error(f"Error when cloning {git_data}")


def clone_main(args, workdir):
    global comments

    if args.show:
        show(args)
    if args.file:
        clone(args, workdir)

    comments = None
