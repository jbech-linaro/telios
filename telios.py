#!/usr/bin/env python3
import argparse
import logging
import os
import sys

import src

from icecream import install
install()

def get_args():
    parser = argparse.ArgumentParser(description='The perfect developer tool\n')
    subparsers = parser.add_subparsers(help='commands', dest="command")

    # Clone parser
    clone_parser = subparsers.add_parser('clone', help='Clone gits')
    clone_parser.add_argument('-f', '--file', action='store', required=False,
                              default=None,
                              help='Manifest file')
    clone_parser.add_argument('-s', '--show', action='store_true', required=False,
                              default=False,
                              help='Show all gits to clone')
    clone_parser.add_argument('-c', '--clean', action='store_true', required=False,
                              default=False,
                              help='Clean gits (i.e., git clean -xdf)')
    clone_parser.add_argument('-u', '--update', action='store_true', required=False,
                              default=False,
                              help='Runs \'git remote update\' on existing gits')
    clone_parser.add_argument('-w', '--wipe', action='store_true', required=False,
                              default=False,
                              help='Wipe gits, i.e., force re-cloning of gits')
    clone_parser.add_argument('--wipe-mirrors', action='store_true', required=False,
                              default=False,
                              help='Wipe all mirrors')
    clone_parser.add_argument('-j', '--jobs', action='store', required=False,
                              default=1, type=int,
                              help='How many jobs to run in parallel')

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()


def init_logger():
    LOG_FMT = ("[%(levelname)s] %(funcName)s():%(lineno)d   %(message)s")
    logging.basicConfig(
        #filename=settings.log_file(),
        level=logging.INFO,
        format=LOG_FMT)


def main():
    init_logger()
    args = get_args()
    #src.load_config()

    workdir = os.environ.get('TELIOS_WORKDIR', '/dev/shm/telios')

    if args.command == "clone":
        src.clone_main(args, workdir)
    else:
        logging.error("No command given")

    print("Done!")


if __name__ == "__main__":
    main()
