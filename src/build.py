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
    def __init__(self, data, workspace, args):
        self.workspace = workspace
        self.args = args

        self.name = data['name']
        self.url = data['url']
        self.commit = data['commit']

        self.depends_on = data.get('depends_on', None)
        self.task_workdir = f"{workspace}/{self.name}"
        self.telios_yml = f"{self.task_workdir}/telios.yml"
        self.override_yml = f"{workspace}/override/{self.name}.yml"

        self.initialized_log = None
        self.stderr_log = [f"{workspace}/errors/{self.name}-stderr.log", None]
        self.stdout_log = [f"{workspace}/errors/{self.name}-stdout.log", None]


    def __del__(self):
        if self.stdout_log[1]:
            logging.debug(f"{self.name}: close stdout log file")
            self.stdout_log[1].close()

        if self.stderr_log[1]:
            self.stderr_log[1].close()
            logging.debug(f"{self.name}: close stderr log file")


    def get_dependencies(self):
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
            return []

        nbr_stages = yml.get(stage, None)
        if nbr_stages is None:
            logging.debug(f"Nothing to do for {self.name} : {stage}")
            return []

        cmds = yml[stage]
        return cmds

    @staticmethod
    def _make_command_list(parameters):
        param_list = []
        if parameters:
            for p in parameters.split():
                param_list.append(p)
        return param_list


    def _print_and_write(self, stdout, stderr):
        if stdout:
            print(stdout, end='')
            if self.args.log_stdout:
                if not self.stdout_log[1]:
                    logging.debug(f"{self.name}: open stdout log file")
                    self.stdout_log[1] = open(self.stdout_log[0], 'w')
                self.stdout_log[1].write(f"{stdout}")

        if stderr:
            print(stderr, end='')
            if self.args.log_stderr:
                if not self.stderr_log[1]:
                    logging.debug(f"{self.name}: open stderr log file")
                    self.stderr_log[1] = open(self.stderr_log[0], 'w')
                self.stderr_log[1].write(f"{stderr}")

    # This will run, print and eventually log stdout and stderr. However, the
    # order will always be stdout then stderr. I.e., they won't be interleaved
    # as would be seen when running this directly from commandline.
    def _run(self, cmd, stage, parameters):
        log_cmd = f"[build:{self.name}:{stage}] {cmd} {parameters if parameters else ''}\n"
        self._print_and_write(log_cmd, None)
        try:
            param_list = self._make_command_list(parameters)
            proc = subprocess.run([cmd] + param_list, cwd=self.task_workdir, text=True,
                                  capture_output=True)
            for line in proc.stdout:
                self._print_and_write(line, None)

            if proc.returncode != 0:
                # Send the log_cmd here to make easier to see in the stderro
                # log what caused the error.
                self._print_and_write(None, log_cmd)
                extra = f"[build:{self.name}:{stage}] ERROR rc={proc.returncode}\n"
                self._print_and_write(None, extra)
                for line in proc.stderr:
                    self._print_and_write(None, line)
        except FileNotFoundError:
            self._print_and_write(None, log_cmd)
            extra = f"[build:{self.name}:{stage}] ERROR Cannot find command '{cmd}'\n"
            self._print_and_write(None, extra)


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


def gather_projects(args, workspace):
    yml = src.load_yml(args.file)
    nbr_gits = len(yml['gits'])
    if nbr_gits < 1:
        return None

    print(f"[build] {nbr_gits} gits found in {args.file} ...")

    projects = {}
    for git_data in yml['gits']:
        projects[git_data['name']] = Project(git_data, workspace, args)

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


def build_main(args, workspace):
    print(f"Telios build (-j{args.jobs})")
    projects = gather_projects(args, workspace)
    if args.log_stdout or args.log_stderr:
        create_error_log_dir(f"{workspace}/errors")
    dag = run(projects, args.jobs)
