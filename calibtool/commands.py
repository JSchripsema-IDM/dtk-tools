import argparse
from importlib import import_module
import os
import sys

from simtools.SetupParser import SetupParser


def load_config_module(config_name):
    config_name = config_name.replace('\\', '/')
    if '/' in config_name:
        splitted = config_name.split('/')[:-1]
        sys.path.append(os.path.join(os.getcwd(), *splitted))
    else:
        sys.path.append(os.getcwd())

    module_name = os.path.splitext(os.path.basename(config_name))[0]
    return import_module(module_name)


def get_calib_manager_args(args, unknownArgs, force_metadata=False):
    mod = load_config_module(args.config_name)
    manager = mod.calib_manager
    calib_args = mod.run_calib_args

    # DJK: This function previously attempted to recover the 'selected_block' from the latest IterationState.json cache.  However, this functionality was buggy and required many bespoke lines of code in CalibManager.  A better solution is needed if this feature is required.

    # update ini
    manager_data = manager.read_calib_data(True)
    calib_args['ini'] = manager_data['setup_overlay_file'] if manager_data else None
    update_calib_args(args, unknownArgs, calib_args)

    return manager, calib_args


def update_calib_args(args, unknownArgs, calib_args):
    if hasattr(args,'priority') and args.priority:
        calib_args['priority'] = args.priority
    if hasattr(args,'node_group') and args.node_group:
        calib_args['node_group'] = args.node_group

    # Get the proper configuration block.
    if len(unknownArgs) == 0:
        selected_block = calib_args['selected_block'] if ('selected_block' in calib_args and calib_args['selected_block']) else "LOCAL"
    elif len(unknownArgs) == 1:
        selected_block = unknownArgs[0][2:].upper()
    else:
        raise Exception('Too many unknown arguments: please see help.')

    # Update the setupparser
    SetupParser(selected_block=selected_block, setup_file=args.ini if hasattr(args,'ini') and args.ini else calib_args['ini'], force=True)


def run(args, unknownArgs):
    manager, calib_args = get_calib_manager_args(args, unknownArgs)
    manager.run_calibration(**calib_args)


def resume(args, unknownArgs):
    manager, calib_args = get_calib_manager_args(args, unknownArgs, force_metadata=True)
    manager.resume_from_iteration(args.iteration,
                                  iter_step=args.iter_step,
                                  **calib_args)


def reanalyze(args, unknownArgs):
    manager, calib_args = get_calib_manager_args(args, unknownArgs, force_metadata=True)
    if args.iteration is not None:
        manager.reanalyze_iteration(args.iteration)
    else:
        manager.reanalyze()

def cleanup(args, unknownArgs):
    mod = load_config_module(args.config_name)
    manager = mod.calib_manager
    # If no result present -> just exit
    if not os.path.exists(os.path.join(os.getcwd(), manager.name)):
        print 'No calibration to delete. Exiting...'
        exit()
    manager.cleanup()


def kill(args, unknownArgs):
    mod = load_config_module(args.config_name)
    manager = mod.calib_manager
    manager.kill()


def replot(args, unknownArgs):
    manager, calib_args = get_calib_manager_args(args, unknownArgs, force_metadata=True)
    manager.replot(args.iteration)


def main():

    parser = argparse.ArgumentParser(prog='calibtool')
    subparsers = parser.add_subparsers()

    # 'calibtool run' options
    parser_run = subparsers.add_parser('run', help='Run a calibration configured by run-options')
    parser_run.add_argument(dest='config_name', default=None, help='Name of configuration python script for custom running of calibration.')
    parser_run.add_argument('--ini', default=None, help='Specify an overlay configuration file (*.ini).')
    parser_run.add_argument('--priority', default=None, help='Specify priority of COMPS simulation (only for HPC).')
    parser_run.add_argument('--node_group', default=None, help='Specify node group of COMPS simulation (only for HPC).')
    parser_run.set_defaults(func=run)

    # 'calibtool resume' options
    parser_resume = subparsers.add_parser('resume', help='Resume a calibration configured by resume-options')
    parser_resume.add_argument(dest='config_name', default=None, help='Name of configuration python script for custom running of calibration.')
    parser_resume.add_argument('--iteration', default=None, type=int, help='Resume calibration from iteration number (default is last cached state).')
    parser_resume.add_argument('--iter_step', default=None, help="Resume calibration on specified iteration step ['commission', 'analyze', 'next_point'].")
    parser_resume.add_argument('--ini', default=None, help='Specify an overlay configuration file (*.ini).')
    parser_resume.add_argument('--priority', default=None, help='Specify priority of COMPS simulation (only for HPC).')
    parser_resume.add_argument('--node_group', default=None, help='Specify node group of COMPS simulation (only for HPC).')
    parser_resume.set_defaults(func=resume)

    # 'calibtool reanalyze' options
    parser_reanalyze = subparsers.add_parser('reanalyze', help='Rerun the analyzers of a calibration')
    parser_reanalyze.add_argument(dest='config_name', default=None, help='Name of configuration python script for custom running of calibration.')
    parser_reanalyze.add_argument('--iteration', default=None, type=int, help='Resume calibration from iteration number (default is last cached state).')
    parser_reanalyze.set_defaults(func=reanalyze)

    # 'calibtool cleanup' options
    parser_cleanup = subparsers.add_parser('cleanup', help='Cleanup a calibration')
    parser_cleanup.add_argument(dest='config_name', default=None,
                               help='Name of configuration python script for custom running of calibration.')
    parser_cleanup.set_defaults(func=cleanup)

    # 'calibtool kill' options
    parser_cleanup = subparsers.add_parser('kill', help='Kill a calibration')
    parser_cleanup.add_argument(dest='config_name', default=None,
                               help='Name of configuration python script.')
    parser_cleanup.set_defaults(func=kill)

    # 'calibtool plotter' options
    parser_replot = subparsers.add_parser('replot', help='Re-plot a calibration configured by plotter-options')
    parser_replot.add_argument(dest='config_name', default=None, help='Name of configuration python script for custom running of calibration.')
    parser_replot.add_argument('--iteration', default=None, type=int, help='Replot calibration for one iteration (default is to iterate over all).')
    parser_replot.set_defaults(func=replot)

    # run specified function passing in function-specific arguments
    args, unknownArgs = parser.parse_known_args()
    args.func(args, unknownArgs)

if __name__ == '__main__':
    main()
