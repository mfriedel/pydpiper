#!/usr/bin/env python

from pydpiper.application import AbstractApplication
from pydpiper.pipeline import Pipeline, CmdStage, InputFile, OutputFile, LogFile
import pydpiper.file_handling as fh
import pydpiper_apps.minc_tools.registration_functions as rf
import pydpiper_apps.minc_tools.registration_file_handling as rfh
import pydpiper_apps.minc_tools.minc_modules as mm
import pydpiper_apps.minc_tools.minc_atoms as ma
import pydpiper_apps.minc_tools.stats_tools as st
import Pyro
from datetime import date, datetime
from os.path import abspath, isdir
from os import walk
import fnmatch
import logging
import csv
import sys

logger = logging.getLogger(__name__)

Pyro.config.PYRO_MOBILE_CODE=1 

def getLsq6AndXfms(nlinFH, subjects, lsq6Files, time, mbmDir, processedDirectory):

    """For each file in the build-model registration (associated with the specified
       time point), do the following:
       
       1. Find the to-native.xfm for that file. 
       2. Find the matching subject at the specified time point
       3. Set this xfm to be the last xfm from nlin average to subject from step #2. 
       4. Find the -from-native.xfm file.
       5. Set this xfm to be the last xfm from subject to nlin.
       
       Note: assume that the names in processedDir match beginning file 
             names in subject
    """
     
    baseNames = walk(mbmDir).next[1]
    for b in baseNames:
        xfmToNative = abspath(mbmDir + "/" + b + "/transforms/" + b + "-to-native.xfm")
        xfmFromNative = abspath(mbmDir + "/" + b + "/transforms/" + b + "-from-native.xfm")
        lsq6Resampled = abspath(mbmDir + "/" + b + "/resampled/" + b + "-lsq6.mnc")
        for s in subjects:
            if fnmatch.fnmatch(s[time], "*" + b + "*"):
                nlinFH.setLastXfm(s[time], xfmToNative)
                s[time].setLastXfm(nlinFH, xfmFromNative)
                lsq6Files[s[time]] = rfh.RegistrationFHBase(lsq6Resampled, processedDirectory)
                break

def concatAndResample(subjects, subjectStats, timePoint, nlinFH, blurs):
    """For each subject, take the deformation fields and resample them into the nlin-3 space.
       The transforms that are concatenated depend on which time point is used for the average"""
    pipeline = Pipeline()
    for s in subjects:
        # xfmToNlin will be either to lsq6 or native depending on other factors
        # may need an additional argument for this function
        xfmToNlin = s[timePoint].getLastXfm(nlinFH)
        xfmArray = [xfmToNlin]
        count = len(subjects[s])
        for b in blurs:
            """Do timePoint with average first"""
            res = resampleToCommon(xfmToNlin, s[timePoint], subjectStats[s][timePoint], b, nlinFH)
            pipeline.addPipeline(res)
            if not timePoint - 1 < 0:
                """Average happened at time point other than first time point. 
                   Loop over points prior to average."""
                for i in reversed(range(timePoint)):
                    xcs = getAndConcatXfm(s[i], subjectStats[s], i, xfmArray, False)
                    pipeline.addStage(xcs)
                    res = resampleToCommon(xcs.outputFiles[0], s[i], subjectStats[s][i], b, nlinFH)
                    pipeline.addPipeline(res)
            """Loop over points after average. If average is at first time point, this loop
               will hit all time points (other than first). If average is at subsequent time 
               point, it hits all time points not covered previously."""
            xfmArray=[xfmToNlin]    
            for i in range(timePoint + 1, count-1):
                xcs = getAndConcatXfm(s[i], subjectStats[s], i, xfmArray, True)
                pipeline.addStage(xcs)
                res = resampleToCommon(xcs.outputFiles[0], s[i], subjectStats[s][i], b, nlinFH)
                pipeline.addPipeline(res)
    return pipeline

def getAndConcatXfm(s, subjectStats, i, xfmArray, inverse):
    """Insert xfms into array and concat, returning CmdStage
       Note that s is s[i] and subjectStats is subjectStats[s] from calling function
       inverse=True means that we need to retrieve inverse transforms"""
       
    if inverse:
        xfm = subjectStats[i-1].inverseXfm
    else:
        xfm = subjectStats[i].transform
    xfmArray.insert(0, xfm)
    output = fh.createBaseName(s.setOutputDirectory("stats"), "xfm_to_common_space.xfm")
    cmd = ["xfmconcat", "-clobber"] + [InputFile(a) for a in xfmArray] + [OutputFile(output)]
    
    xfmConcat = CmdStage(cmd)
    xfmConcat.setLogFile(LogFile(fh.logFromFile(s.logDir, output)))
    return xfmConcat
    
    
def resampleToCommon(xfm, s, subjectStats, b, nlinFH):
    """Note that subject is s[timePoint] and
       subjectStats is subjectStats[s][timepoint] in calling function"""
    pipeline = Pipeline()
    outputDirectory = s.setOutputDirectory("stats")
    
    filesToResample = [subjectStats.jacobians[b], subjectStats.scaledJacobians[b]]
    for f in filesToResample:
        outputBase = fh.removeBaseAndExtension(f).split(".mnc")[0]
        outputFile = fh.createBaseName(outputDirectory, outputBase + "_common" + ".mnc")
        logFile = fh.logFromFile(s.logDir, outputFile)
        res = ma.mincresample(f, 
                              nlinFH.getLastBaseVol(),
                              transform = xfm,
                              outfile=outputFile,
                              logFile=logFile) 
        pipeline.addStage(res)
    
    return pipeline

class RegistrationChain(AbstractApplication):
    def setup_options(self):
        self.parser.add_option("--pipeline-name", dest="pipeline_name",
                      type="string", default=None,
                      help="Name of pipeline and prefix for models.")
        self.parser.add_option("--pipeline-dir", dest="pipeline_dir",
                      type="string", default=".",
                      help="Directory for placing pipeline results. Default is current.")
        self.parser.add_option("--init-model", dest="init_model",
                      type="string", default=None,
                      help="Name of file to register towards. If unspecified, bootstrap.")
        self.parser.add_option("--reg-type", dest="reg_type",
                      type="string", default="mincANTS",
                      help="Type of registration. Options are mincANTS (default) and minctracc.")
        self.parser.add_option("--avg-time-point", dest="avg_time_point",
                      type="int", default=1,
                      help="Time point we average first (if doing --partial-align) to get nlin space.")
        self.parser.add_option("--stats-kernels", dest="stats_kernels",
                      type="string", default="1.0,0.5,0.2,0.1", 
                      help="comma separated list of blurring kernels for analysis. Default is: 1.0,0.5,0.2,0.1")
        self.parser.add_option("--MBM-directory", dest="mbm_dir",
                      type="string", default=None, 
                      help="_processed directory from MBM used to average specified time point.")
        self.parser.add_option("--nlin-average", dest="nlin_avg",
                      type="string", default=None, 
                      help="Final nlin average from MBM run.")
        self.parser.add_option("--native-or-lsq6", dest="native_or_lsq6",
                      type="string", default="native", 
                      help="View final output in native (default) or lsq6 space.")
        
        self.parser.set_usage("%prog [options] input.csv") 

    def setup_backupDir(self):
        """Output directory set here as well. backups subdirectory automatically
        placed here so we don't need to set via the command line"""
        backup_dir = fh.makedirsIgnoreExisting(self.options.pipeline_dir)    
        self.pipeline.setBackupFileLocation(backup_dir)

    def setup_appName(self):
        appName = "Longitudinal-registration"
        return appName
    
    def setup_logger(self):
        FORMAT = '%(asctime)-15s %(name)s %(levelname)s: %(message)s'
        now = datetime.now()  
        FILENAME = str(self.appName) + "-" + now.strftime("%Y%m%d-%H%M%S") + ".log"
        logging.basicConfig(filename=FILENAME, format=FORMAT, level=logging.DEBUG)

    def run(self):
        options = self.options
        args = self.args
        self.reconstructCommand()
        
        """Directory handling etc as in MBM"""
        pipeDir = fh.makedirsIgnoreExisting(options.pipeline_dir)
        if not options.pipeline_name:
            pipeName = str(date.today()) + "_pipeline"
        else:
            pipeName = options.pipeline_name
        
        processedDirectory = fh.createSubDir(pipeDir, pipeName + "_processed")
        
        """Read in files from csv"""
        fileList = open(args[0], 'rb')
        subjectList = csv.reader(fileList, delimiter=',', skipinitialspace=True)
        subjects = {} # One array of images for each subject
        index = 0 
        for subj in subjectList:
            subjects[index] = rf.initializeInputFiles(subj, processedDirectory)
            index += 1
        
        """Put blurs into array"""
        blurs = []
        for i in options.stats_kernels.split(","):
            blurs.append(float(i))
        
        """Create file handler for nlin average from MBM"""
        if options.nlin_avg:
            nlinFH = rfh.RegistrationFHBase(abspath(options.nlin_avg), processedDirectory)
        if options.mbm_dir and not isdir(abspath(options.mbm_dir)):
            logger.error("The --mbm-directory specified does not exist: " + abspath(options.mbm_dir))
            sys.exit()
        
        """lsq6Files from MBM run will be file handlers indexed by s[time]"""
        lsq6Files = {}
        
        """Take average time point, subtract 1 for proper indexing"""
        avgTime = options.avg_time_point - 1
        
        """Get transforms from inputs to final nlin average and vice versa as well as lsq6 files"""
        if options.nlin_avg and options.mbm_dir:
            getLsq6AndXfms(nlinFH, 
                           subjects, 
                           lsq6Files, 
                           avgTime, 
                           abspath(options.mbm_dir), 
                           processedDirectory)
        
            """Align everything to lsq6 space, with ordering depending on time point"""
            lsq6Pipe = mm.ChainAlignLSQ6(subjects, avgTime, lsq6Files)
            self.p.addPipeline(lsq6Pipe)
        else:
            logger.info("MBM directory and nlin_average not specified.")
            logger.info("Calculating registration chain only")
        
        """Create a dictionary of statistics. Each subject gets an array of statistics
           indexed by timepoint. The indexing on the subjectStats dictionary should match
           the subjects dictionary"""
        subjectStats = {}
        
        for subj in subjects:
            subjectStats[subj] = {}
            s = subjects[subj]
            count = len(s) 
            for i in range(count - 1):
                # Create new groups
                # if/else here for minctracc/mincANTS
                p = mm.HierarchicalMinctracc(s[i], s[i+1])
                self.pipeline.addPipeline(p)
                """Resample s[i] into space of s[i+1]""" 
                resample = ma.mincresample(s[i], s[i+1], likeFile=nlinFH)
                self.pipeline.addStage(resample)
                lastXfm = s[i].getLastXfm(s[i+1])
                # not sure if want to use new group or existing
                """Initialize newGroup with initial file as i resampled to i+1 
                   space and setLastXfm to be final xfm from original group"""
                groupName = "time_point_" + str(i) + "_to_" + str(i+1) 
                s[i].newGroup(inputVolume=resample.outputFiles[0], groupName=groupName) 
                s[i].setLastXfm(s[i+1], lastXfm)
                # like file should be nlin-3.mnc
                stats = st.CalcStats(s[i], s[i+1], blurs)
                self.pipeline.addPipeline(stats.p)
                subjectStats[subj][i] = stats.statsGroup
        
        """Now that all registration is complete, concat transforms and resample"""
        if options.nlin_avg and options.mbm_dir:
            car = concatAndResample(subjects, subjectStats, avgTime, nlinFH, blurs) 
            self.pipeline.addPipeline(car)
            

if __name__ == "__main__":
    
    application = RegistrationChain()
    application.start()