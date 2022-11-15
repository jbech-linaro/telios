import src
import logging
from graphlib import TopologicalSorter
from graphlib import CycleError

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


def create_dag(projects):
    ts = TopologicalSorter()
    dag = None
    for name, obj in projects.items():
        for dependency in obj.get_dependencies():
            ts.add(name, dependency)
            #print(dependency)

    try:
        dag = ts.static_order()
        #print(tuple(dag))
    except CycleError as e:
        logging.error(f"You have a cyclic dependency in the manifest\n  {e}")
        exit()

    return dag


def print_build_order(dag):
    print("Build order:")
    i = 0
    for x in dag:
        print(f"  {i}: {x}")
        i += 1


def build_main(args, workdir):
    print("Running the build stage")
    projects = gather_projects(args, workdir)
    dag = create_dag(projects)
    print_build_order(dag)
