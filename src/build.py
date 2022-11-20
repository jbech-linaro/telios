import logging
import shutil
import time
import os
import subprocess

from concurrent.futures import ProcessPoolExecutor, as_completed
from graphlib import TopologicalSorter
from threading import Thread, active_count
from queue import Queue
from random import randrange
from datetime import datetime

import src

stages = ["configure", "compile", "assemble", "deploy"]

class Project():
    def __init__(self, data, workdir, args):
        self.name = data['name']
        self.url = data['url']
        self.commit = data['commit']
        self.depends_on = data.get('depends_on', None)
        self.args = args
        self.workdir = workdir
        self.task_workdir = f"{workdir}/{data['name']}"
        self.telios_yml = f"{self.task_workdir}/telios.yml"
        self.override_yml = f"{workdir}/override/{data['name']}.yml"
        self.error_log = f"{workdir}/errors/{data['name']}.log"
        self.initialized_log = None


    def get_dependencies(self) -> list[str]:
        if self.depends_on is None:
            return []
        return self.depends_on.split()


    def _get_commands(self, stage):
        yml_file = self.telios_yml
        if os.path.isfile(self.override_yml):
            logging.debug(f"[build:{self.name}:{stage}] Using overide file: {yml_file}")
            yml_file = self.override_yml

        try:
            yml = src.load_yml(yml_file)
        except FileNotFoundError:
            pass
            return []

        nbr_stages = yml.get(stage, None)
        if nbr_stages is None:
            logging.debug(f"Nothing to do for {self.name} : {stage}")
            return []
        cmds = yml[stage]
        return cmds


    def _log_error(self, message):
        if self.initialized_log is None:
            with open(self.error_log, 'w') as f:
                f.write(message)
                self.initialized_log = True
        else:
            with open(self.error_log, 'a') as f:
                f.write(f"\n{message}")


    def _open_error_log(self):
        if self.initialized_log is None:
            f = open(self.error_log, 'w')
            self.initialized_log = True
        else:
            f = open(self.error_log, 'a')
        return f


    def _run(self, cmd, stage, parameters):
        complete_cmd = [cmd]

        if parameters is not None:
            for p in parameters.split():
                complete_cmd.append(p)

        print(f"[build:{self.name}:{stage}] {cmd} {parameters if parameters is not None else ''}")
        file_or_pipe = subprocess.STDOUT
        if self.args.log_errors:
            file_or_pipe = self._open_error_log()
        try:
            with subprocess.Popen(complete_cmd, cwd=self.task_workdir, text=True,
                                  stdout=subprocess.PIPE, stderr=file_or_pipe) as proc:
                for line in proc.stdout:
                    print(line, end='')

                proc.wait()

                if proc.returncode != 0:
                    print(f"[build:{self.name}:{stage}:ERROR ({proc.returncode})] {proc.stderr}")
        except FileNotFoundError:
            message = f"ERROR: Cannot find command '{cmd}'"
            print(message)
            #self._log_error(f"{message}\n")

        if self.args.log_errors:
            file_or_pipe.close()


    def _run_commands(self, cmds, stage):
        for c in cmds:
            cmd = c.get('cmd', None)
            if cmd is None:
                logging.error(f"cmd key without an actual command in (FIXME add correct file)")
                return

            parameters = c.get('parameter', None)
            self._run(cmd, stage, parameters)


    def run(self):
        global stages
        for stage in stages:
            cmds = self._get_commands(stage)
            self._run_commands(cmds, stage)
            time.sleep(0.1)


    def __str__(self):
        return f"Project {self.name}\n {self.url} : {self.commit}\n {self.depends_on}"


def gather_projects(args, workdir):
    yml = src.load_yml(args.file)
    nbr_gits = len(yml['gits'])
    if nbr_gits < 1:
        return None

    print(f"[build] {nbr_gits} gits found in {args.file} ...")

    projects = {}
    for git_data in yml['gits']:
        projects[git_data['name']] = Project(git_data, workdir, args)

    return projects


def worker(node, projects):
    project = projects[node]
    start = time.time()
    project.run()
    end = time.time()
    delta = round(end - start, 2)
    print(f"[build:{node}:done] ran for {delta} seconds")
    return node


def run(projects, jobs):
    ts = TopologicalSorter()

    # Create the DAG, always add "itself".
    for name, obj in projects.items():
        ts.add(name)
        for dependency in obj.get_dependencies():
            ts.add(name, dependency)

    ts.prepare()
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        while ts.is_active():
            # Make a list of independent jobs, ready to run
            pending = []
            for node in ts.get_ready():
                pending.append(node)

            # Run all independant jobs
            results = [executor.submit(worker, n, projects) for n in pending]
            for job in as_completed(results):
                res = job.result()
                ts.done(res)


# FIXME: This function feels bad
def create_error_log_dir(mirror_dir):
    print(f"Setting up log dir for errors: {mirror_dir}")
    try:
        shutil.rmtree(mirror_dir)
    except (OSError, FileNotFoundError):
        pass

    os.makedirs(mirror_dir)


def build_main(args, workdir):
    print(f"Telios build (-j{args.jobs})")
    projects = gather_projects(args, workdir)
    if args.log_errors:
        create_error_log_dir(f"{workdir}/errors")
    dag = run(projects, args.jobs)
