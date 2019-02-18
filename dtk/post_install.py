import ctypes
import sys
import os
import argparse
from dtk import post_helper


def setup_post():
    post_helper.handle_master_ini(True)


def setup_init(args, unknownArgs):
    post_helper.handle_master_ini()


def setup_examples(args, unknownArgs):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    site_pkg_path = os.path.dirname(current_directory)

    src = os.path.join(site_pkg_path, 'examples')

    if not os.path.isdir(src):
        print("Examples location '{}' doesn't exist!".format(src))
        return

    if args.output is None:
        args.output = '.'

    if not os.path.isdir(args.output):
        print("Output location '{}' doesn't exist!".format(args.output))
        return

    # construct user examples folder
    output = os.path.abspath(args.output)
    example_folder = os.path.join(output, 'examples')

    # copy examples to user location
    post_helper.copy(src, example_folder)

    # set up ini files for examples
    post_helper.handle_examples_ini(example_folder)


def setup_migrate(args, unknownArgs):
    post_helper.backup_db()
    post_helper.cleanup_locks()


def setup_start(args, unknownArgs):
    if args.output is None:
        args.output = '.'

    if not os.path.isdir(args.output):
        print("Location '{}' doesn't exist!".format(args.output))
        return

    pj_name = unknownArgs[0] if len(unknownArgs) > 0 else 'New Project'
    post_helper.start(os.path.abspath(args.output), pj_name)


def main():
    # parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(prog='dtksetup')
    subparsers = parser.add_subparsers()

    # post: a testing...
    parser_clearbatch = subparsers.add_parser('post', help='Run dtksetup post.')
    parser_clearbatch.set_defaults(func=setup_post)

    # setup ini
    parser_clearbatch = subparsers.add_parser('init', help='Setup init files.')
    parser_clearbatch.set_defaults(func=setup_init)

    # copy dtk examples to user location
    parser_clearbatch = subparsers.add_parser('examples', help='Copy DTK-TOOLS Examples to user location.')
    parser_clearbatch.add_argument('-o', '--output', dest='output', required=False,
                                   help='Location to copy examples to.')
    parser_clearbatch.set_defaults(func=setup_examples)

    # backup db
    parser_clearbatch = subparsers.add_parser('migrate', help='Backup existing db.')
    parser_clearbatch.set_defaults(func=setup_migrate)

    # setup boilerplate for new project
    parser_clearbatch = subparsers.add_parser('start', help='Setup a new project with boilerplate.')
    parser_clearbatch.add_argument('-o', '--output', dest='output', required=False,
                                   help='Location to setup a new project.')
    parser_clearbatch.set_defaults(func=setup_start)

    # run specified function passing in function-specific arguments
    args, unknownArgs = parser.parse_known_args()

    # This is it! This is where SetupParser gets set once and for all. Until you run 'dtk COMMAND' again, that is.
    # init.initialize_SetupParser_from_args(args, unknownArgs)

    args.func(args, unknownArgs)

    # Success !
    print("\nThe action is complete.")


if __name__ == "__main__":
    # check os first
    if ctypes.sizeof(ctypes.c_voidp) != 8 or sys.version_info < (3, 6):
        print("""\nFATAL ERROR: dtk-tools only supports Python 3.6 x64 and above.\n
         Please download and install a x86-64 version of python at:\n
        - Windows: https://www.python.org/downloads/windows/
        - Mac OSX: https://www.python.org/downloads/mac-osx/
        - Linux: https://www.python.org/downloads/source/\n
        Installation is now exiting...""")
        exit()

    main()
