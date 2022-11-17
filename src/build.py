import logging
import time
import subprocess

from graphlib import TopologicalSorter
from graphlib import CycleError
from threading import Thread, active_count
from queue import Queue
from random import randrange

import src

stages = ["configure", "compile", "assemble", "deploy"]

class Project():
    def __init__(self, data, workdir):
        self.name = data['name']
        self.url = data['url']
        self.commit = data['commit']
        self.depends_on = data.get('depends_on', None)
        self.workdir = f"{workdir}/{data['name']}"
        self.telios_yml = f"{self.workdir}/telios.yml"


    def get_dependencies(self) -> list[str]:
        if self.depends_on is None:
            return []
        return self.depends_on.split()


    def _get_commands(self, stage):
        yml_file = self.workdir + "/telios.yml"
        try:
            yml = src.load_yml(yml_file)
        except FileNotFoundError:
            #print(f"Not found: {yml_file}, trying override")
            pass
            return []

        nbr_gits = len(yml[stage])
        if nbr_gits < 1:
            print(f"Nothing to do for {self.name} : {stage}")
            return []
        cmds = yml[stage]
        return cmds


    def _run_command(self, cmd, parameters):
        print(f"[{self.name}:run] {cmd} {parameters}")
        complete_cmd = [cmd]
        for p in parameters.split():
            complete_cmd.append(p)

        try:
            with subprocess.Popen(complete_cmd, stdout=subprocess.PIPE) as proc:
                print(proc.stdout.read().decode("utf-8"))
        except FileNotFoundError:
            logging.error(f"Cannot run command: {cmd}! Not installed? Not in $PATH")


    def _configure(self):
        print(f"Configuring -> {self.name}")
        cmds = self._get_commands("configure")

        for c in cmds:
            print(c)
            cmd = c.get('cmd', None)
            if cmd is None:
                logging.error(f"cmd key without an actual command in {self.telios_yml}")
                return
            parameters = c.get('parameter', "")
            self._run_command(c['cmd'], parameters)


    def _compile(self):
        print(f"Compiling -> {self.name}")


    def _assemble(self):
        print(f"Assemble -> {self.name}")


    def _deploy(self):
        print(f"Deploying -> {self.name}")


    def run(self):
        global stages
        for stage in stages:
            match stage:
                case "configure":
                    self._configure()
                case "compile":
                    self._compile()
                case "assemble":
                    self._assemble()
                case "deploy":
                    self._deploy()
                case _:
                    print("Nothing here")
            #time.sleep(randrange(0, 3))


    def __str__(self):
        return f"Project {self.name}\n {self.url} : {self.commit}\n {self.depends_on}"


def gather_projects(args, workdir):
    yml = src.load_yml(args.file)
    nbr_gits = len(yml['gits'])
    if nbr_gits < 1:
        return None

    print(f"{nbr_gits} gits found in {args.file} ...")

    projects = {}
    for git_data in yml['gits']:
        projects[git_data['name']] = Project(git_data, workdir)

    return projects


def worker(node, projects, ts):
    project = projects[node]
    print(f"\n--> Started {project.name}")
    project.run()
    ts.done(node)
    print(f"<-- Completed {node}")


def run(projects, jobs):
    print(f"Using {jobs} CPU cores")

    ts = TopologicalSorter()

    # Create the DAG, always add "itself".
    for name, obj in projects.items():
        ts.add(name)
        for dependency in obj.get_dependencies():
            ts.add(name, dependency)

    ts.prepare()
    threads = list()
    active_threads = 0
    while ts.is_active():
        for node in ts.get_ready():
            x = Thread(target=worker, args=(node, projects, ts))
            threads.append(x)
            x.start()
            active_threads += 1
            while active_threads >= jobs:
                for index, thread in enumerate(threads):
                    thread.join()
                    threads.pop(index)
                    active_threads -= 1
                    # Just to be on the safe side
                    if active_threads < 0:
                        active_threads = 0


def build_main(args, workdir):
    print(f"Running the build stage (-j {args.jobs})")
    projects = gather_projects(args, workdir)
    dag = run(projects, args.jobs)
