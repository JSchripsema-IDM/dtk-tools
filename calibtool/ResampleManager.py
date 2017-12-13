from calibtool.CalibrationPoints import CalibrationPoints

class ResampleManager:
    def __init__(self, steps, analyzer_path):
        self.steps = steps
        self.analyzer_path = analyzer_path

    def resample_and_run(self, calibrated_points, resample_step, run_args, unknown_args):
        resample_step = 0
        for resampler in self.steps:
            calibrated_points = resampler.resample_and_run(calibrated_points=calibrated_points,
                                                           analyzer_path=self.analyzer_path,
                                                           resample_step=resample_step,
                                                           run_args=run_args,
                                                           unknown_args=unknown_args)
            resample_step += 1
        self.results = calibrated_points

    def write_results(self, filename):
        CalibrationPoints(points=self.results).write(filename=filename)
