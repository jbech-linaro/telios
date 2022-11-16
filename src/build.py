import logging
import time

from graphlib import TopologicalSorter
from graphlib import CycleError
from threading import Thread, active_count
from queue import Queue

import src

stages = ["configure", "compile", "assemble", "deploy"]

class Project():
    def __init__(self, data):
        self.name = data['name']
        self.url = data['url']
        self.commit = data['commit']
        self.depends_on = data.get('depends_on', None)


    def get_dependencies(self) -> list[str]:
        if self.depends_on is None:
            return []
        return self.depends_on.split()

    def _configure(self):
        print(f"Configuring -> {self.name}")


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
            time.sleep(1)


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
        projects[git_data['name']] = Project(git_data)

    return projects


def worker(task_queue, finalized_tasks_queue, projects):
    while True:
        workPiece = task_queue.get()
        project = projects[workPiece]
        print(f"\n--> Started {project.name}")
        project.run()
        task_queue.task_done()
        finalized_tasks_queue.put(workPiece)


def run(projects):
    global stages
    task_queue = Queue()
    finalized_tasks_queue = Queue()
    Thread(target=worker, daemon=True, args=(task_queue, finalized_tasks_queue,
           projects)).start()

    ts = TopologicalSorter()

    # Create the DAG, always add "itself".
    for name, obj in projects.items():
        ts.add(name)
        for dependency in obj.get_dependencies():
            ts.add(name, dependency)

    ts.prepare()
    while ts.is_active():
        for node in ts.get_ready():
            task_queue.put(node)

        node = finalized_tasks_queue.get()
        ts.done(node)
        print(f"<-- Completed {node}")

    task_queue.join()


def print_build_order(dag):
    print("Build order:")
    i = 0
    for x in dag:
        print(f"  {i}: {x}")
        i += 1


def build_main(args, workdir):
    print("Running the build stage")
    projects = gather_projects(args, workdir)
    dag = run(projects)
    #print_build_order(dag)
