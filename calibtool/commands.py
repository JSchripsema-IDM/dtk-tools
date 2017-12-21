import argparse
import os
# from calibtool import commands_args
from calibtool import commands_args
from calibtool.resamplers.ResampleManager import ResampleManager
from simtools.SetupParser import SetupParser
import simtools.Utilities.Initialization as init

def get_calib_manager(args, unknownArgs, force_metadata=False):
    manager = args.loaded_module.calib_manager

    # Update the SetupParser to match the existing experiment environment/block if force_metadata == True
    if force_metadata:
        exp = manager.get_experiment_from_iteration(iteration=args.iteration, force_metadata=force_metadata)
        SetupParser.override_block(exp.selected_block)
    return manager


def get_resample_manager(args, unknownArgs, force_metadata=False):
    mod = args.loaded_module

    if not hasattr(mod, 'run_calib_args') or 'resample_manager' not in mod.run_calib_args:
        warning_note = \
            """
            /!\\ WARNING /!\\ Required to set resample_manager within run_calib_args like the following:

                run_calib_args = {'resample_manager': xxx_manager}
            """
        print(warning_note)
        exit()
    else:
        manager = mod.run_calib_args['resample_manager']

    # Update the SetupParser to match the existing experiment environment/block if force_metadata == True
    if force_metadata:
        exp = manager.get_experiment_from_iteration(iteration=args.iteration, force_metadata=force_metadata)
        SetupParser.override_block(exp.selected_block)

    return manager


def run(args, unknownArgs):
    manager = get_calib_manager(args, unknownArgs)
    manager.run_calibration()


def resample(args, unknownArgs):
    # step 1: Get the resampleManager
    resample_manager = get_resample_manager(args, unknownArgs)

    # step 2: Resample!
    resample_manager.resample()

    # step 3: write final results
    resample_manager.write_results(filename=args.output_filename)


def resume(args, unknownArgs):
    if args.iter_step:
        if args.iter_step not in ['commission', 'analyze', 'plot', 'next_point']:
            print("Invalid iter_step '%s', ignored." % args.iter_step)
            exit()
    manager = get_calib_manager(args, unknownArgs, force_metadata=True)
    manager.resume_calibration(args.iteration, iter_step=args.iter_step)


def cleanup(args, unknownArgs):
    manager = args.loaded_module.calib_manager
    # If no result present -> just exit
    if not os.path.exists(os.path.join(os.getcwd(), manager.name)):
        print('No calibration to delete. Exiting...')
        exit()
    manager.cleanup()


def kill(args, unknownArgs):
    manager = args.loaded_module.calib_manager
    manager.kill()


def main():
    parser = argparse.ArgumentParser(prog='calibtool')
    subparsers = parser.add_subparsers()

    # 'calibtool run' options
    commands_args.populate_run_arguments(subparsers, run)

    # 'calibtool resample' options
    commands_args.populate_resample_arguments(subparsers, resample)

    # 'calibtool resume' options
    commands_args.populate_resume_arguments(subparsers, resume)

    # 'calibtool cleanup' options
    commands_args.populate_cleanup_arguments(subparsers, cleanup)

    # 'calibtool kill' options
    commands_args.populate_kill_arguments(subparsers, kill)

    # run specified function passing in function-specific arguments
    args, unknownArgs = parser.parse_known_args()
    # This is it! This is where SetupParser gets set once and for all. Until you run 'dtk COMMAND' again, that is.
    init.initialize_SetupParser_from_args(args, unknownArgs)
    args.func(args, unknownArgs)

if __name__ == '__main__':
    main()
