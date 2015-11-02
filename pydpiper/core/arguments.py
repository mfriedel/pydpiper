'''
This file will contain argument option groups that can be used 
by PydPiper applications. Some option groups might be mandatory/highly
recommended to add to your application: e.g. the arguments that deal
with the execution of your application.
'''
import time
import os
from pkg_resources import get_distribution

# TODO: most (if not all) of the following options don't do anything yet
# we should come up with a good way to deal with all this. Given that
# Jason wants to be able to connect each of the applications together
# in new code (e.g., by simply calling chain(...args...) or MBM(,,,args...)
# there needs to be another way to create the options hash? So that you could
# write applications that require little to no command line arguments?



def addApplicationArgumentGroup(parser):
    """
    The arguments that all applications share:
    --restart
    --no-restart
    --output-dir
    --create-graph
    --execute
    --no-execute
    --version
    --verbose
    --no-verbose
    files (left over arguments (0 or more is allowed)
    """
    group = parser.add_argument_group("General application options", "General options for all pydpiper applications.")
    group.add_argument("--restart", dest="restart", 
                       action="store_false", default=True,
                       help="Restart pipeline using backup files. [default = %(default)s]")
    group.add_argument("--no-restart", dest="restart", 
                        action="store_false", help="Opposite of --restart")
    # TODO instead of prefixing all subdirectories (logs, backups, processed, ...)
    # with the pipeline name/date, we could create one identifying directory
    # and put these other directories inside
    group.add_argument("--output-dir", dest="output_directory",
                       type=str, default='', #os.getcwd(),
                       help="Directory where output data and backups will be saved.")
    group.add_argument("--create-graph", dest="create_graph",
                       action="store_true", default=False,
                       help="Create a .dot file with graphical representation of pipeline relationships [default = %(default)s]")
    parser.set_defaults(execute=True)
    parser.set_defaults(verbose=False)
    group.add_argument("--execute", dest="execute",
                       action="store_true",
                       help="Actually execute the planned commands [default = %(default)s]")
    group.add_argument("--no-execute", dest="execute",
                       action="store_false",
                       help="Opposite of --execute")
    group.add_argument("--version", action="version",
                       version="%(prog)s ("+get_distribution("pydpiper").version+")", # pylint: disable=E1101                
                       help="Print the version number and exit.")
    group.add_argument("--verbose", dest="verbose",
                       action="store_true",
                       help="Be verbose in what is printed to the screen [default = %(default)s]")
    group.add_argument("--no-verbose", dest="verbose",
                       action="store_false",
                       help="Opposite of --verbose [default]")
    group.add_argument("files", type=str, nargs='*', metavar='file',
                        help='Files to process')



def addExecutorArgumentGroup(parser):
    group = parser.add_argument_group("Executor options",
                        "Options controlling how and where the code is run.")
    group.add_argument("--uri-file", dest="urifile",
                       type=str, default=None,
                       help="Location for uri file if NameServer is not used. If not specified, default is current working directory.")
    group.add_argument("--use-ns", dest="use_ns",
                       action="store_true",
                       help="Use the Pyro NameServer to store object locations. Currently a Pyro nameserver must be started separately for this to work.")
    group.add_argument("--latency-tolerance", dest="latency_tolerance",
                       type=float, default=15.0,
                       help="Allowed grace period by which an executor may miss a heartbeat tick before being considered failed [Default = %(default)s.")
    group.add_argument("--num-executors", dest="num_exec", 
                       type=int, default=-1, 
                       help="Number of independent executors to launch. [Default = %(default)s. Code will not run without an explicit number specified.]")
    group.add_argument("--max-failed-executors", dest="max_failed_executors",
                      type=int, default=2,
                      help="Maximum number of failed executors before we stop relaunching. [Default = %(default)s]")
    # TODO: add corresponding --monitor-heartbeats
    group.add_argument("--no-monitor-heartbeats", dest="monitor_heartbeats",
                      action="store_false",
                      help="Don't assume executors have died if they don't check in with the server (NOTE: this can hang your pipeline if an executor crashes).")
    group.add_argument("--time", dest="time", 
                       type=str, default=None,
                       help="Wall time to request for each server/executor in the format hh:mm:ss. Required only if --queue-type=pbs. Current default on PBS is 48:00:00.")
    group.add_argument("--proc", dest="proc", 
                       type=int, default=1,
                       help="Number of processes per executor. Also sets max value for processor use per executor. [Default = %(default)s]")
    group.add_argument("--mem", dest="mem", 
                       type=float, default=6,
                       help="Total amount of requested memory (in GB) for all processes the executor runs. [Default = %(default)s].")
    group.add_argument("--pe", dest="pe",
                       type=str, default=None,
                       help="Name of the SGE pe, if any. [Default = %(default)s]")
    group.add_argument("--greedy", dest="greedy",
                       action="store_true",
                       help="Request the full amount of RAM specified by --mem rather than the (lesser) amount needed by runnable jobs.  Always use this if your executor is assigned a full node.")
    group.add_argument("--ppn", dest="ppn", 
                       type=int, default=8,
                       help="Number of processes per node. Used when --queue-type=pbs. [Default = %(default)s].")
    group.add_argument("--queue-name", dest="queue_name", type=str, default=None,
                       help="Name of the queue, e.g., all.q (MICe) or batch (SciNet)")
    group.add_argument("--queue-type", dest="queue_type", type=str, default=None,
                       help="""Queue type to submit jobs, i.e., "sge" or "pbs".  [Default = %(default)s]""")
    group.add_argument("--queue-opts", dest="queue_opts",
                       type=str, default="",
                       help="A string of extra arguments/flags to pass to qsub. [Default = %(default)s]")
    group.add_argument("--executor-start-delay", dest="executor_start_delay", type=int, default=180,
                       help="Seconds before starting remote executors when running the server on the grid")
    group.add_argument("--time-to-seppuku", dest="time_to_seppuku", 
                       type=int, default=1,
                       help="The number of minutes an executor is allowed to continuously sleep, i.e. wait for an available job, while active on a compute node/farm before it kills itself due to resource hogging. [Default = %(default)s]")
    group.add_argument("--time-to-accept-jobs", dest="time_to_accept_jobs", 
                       type=int,
                       help="The number of minutes after which an executor will not accept new jobs anymore. This can be useful when running executors on a batch system where other (competing) jobs run for a limited amount of time. The executors can behave in a similar way by given them a rough end time. [Default = %(default)s]")
    group.add_argument('--local', dest="local", action='store_true', help="Don't submit anything to any specified queueing system but instead run as a server/executor")
    group.add_argument("--config-file", type=str, metavar='config_file', is_config_file=True,
                       required=False, help='Config file location')
    group.add_argument("--prologue-file", type=str, metavar='file',
                       help="Location of a shell script to inline into PBS submit script to set paths, load modules, etc.")
    group.add_argument("--min-walltime", dest="min_walltime", type=int, default = 0,
            help="Min walltime (s) allowed by the queuing system [Default = %(default)s]")
    group.add_argument("--max-walltime", dest="max_walltime", type=int, default = None,
            help="Max walltime (s) allowed for jobs on the queuing system, or infinite if None [Default = %(default)s]")
    group.add_argument("--default-job-mem", dest="default_job_mem",
                       type=float, default = 1.75,
                       help="Memory (in GB) to allocate to jobs which don't make a request. [Default=%(default)s]")

def addGeneralRegistrationArgumentGroup(parser):
    group = parser.add_argument_group("General registration options",
                         "General options for running various types of registrations.")
    group.add_argument("--pipeline-name", dest="pipeline_name", type=str,
                       default=time.strftime("pipeline-%d-%m-%Y-at-%H-%m-%S"),
                       help="Name of pipeline and prefix for models.")
    group.add_argument("--input-space", dest="input_space",
                       type=str, default="native", 
                       help="Option to specify space of input-files. Can be native, lsq6, lsq12. "
                            "Native means that there is no prior formal alignent between the input files " 
                            "yet. lsq6 means that the input files have been aligned using translations "
                            "and rotations; the code will continue with a 12 parameter alignment. lsq12 " 
                            "means that the input files are fully linearly aligned. Only non linear "
                            "registrations are performed. [Default=%(default)s]")
    group.add_argument("--registration-resolution", dest="registration_resolution",
                       type=float, default=None,
                       help="Specify the resolution at which you want the registration to be run. "
                            "If not specified, the resolution of the target of your pipeline will "
                            "be used. [Default=%(default)s]")

def addLSQ6ArgumentGroup(parser):
    """
        standard options for the LSQ6 module
    """
    group = parser.add_argument_group("LSQ6-registration options", "Options for performing a 6 parameter (rigid) registration.")
    parser.set_defaults(lsq6_method="lsq6_large_rotations")
    parser.set_defaults(nuc=True)
    parser.set_defaults(inormalize=True)
    parser.set_defaults(copy_header_info=False)
    parser.set_defaults(run_lsq6=True)
    group.add_argument("--run-lsq6", dest="run_lsq6",
                       action="store_true",
                       help="Actually run the 6 parameter alignment [default = %(default)s]")
    group.add_argument("--no-run-lsq6", dest="run_lsq6",
                       action="store_false",
                       help="Opposite of --run-lsq6")
    group.add_argument("--init-model", dest="init_model",
                       type=str, default=None,
                       help="File in standard space in the initial model. The initial model "
                       "can also have a file in native space and potentially a transformation "
                       "file. See our wiki (https://wiki.mouseimaging.ca/) for detailed "
                       "information on initial models. [Default = %(default)s]")
    group.add_argument("--lsq6-target", dest="lsq6_target",
                       type=str, default=None,
                       help="File to be used as the target for the 6 parameter alignment. "
                       "[Default = %(default)s]")
    group.add_argument("--bootstrap", dest="bootstrap",
                       action="store_true", default=False,
                       help="Use the first input file to the pipeline as the target for the "
                       "6 parameter alignment. [Default = %(default)s]")
    # TODO: do we need to implement this option? This was for Kieran Short, but the procedure
    # he will be using in the future most likely will not involve this option.
    #group.add_argument("--lsq6-alternate-data-prefix", dest="lsq6_alternate_prefix",
    #                   type=str, default=None,
    #                   help="Specify a prefix for an augmented data set to use for the 6 parameter "
    #                   "alignment. Assumptions: there is a matching alternate file for each regular input "
    #                   "file, e.g. input files are: input_1.mnc input_2.mnc ... input_n.mnc. If the "
    #                   "string provided for this flag is \"aug_\", then the following files should exists: "
    #                   "aug_input_1.mnc aug_input_2.mnc ... aug_input_n.mnc. These files are assumed to be "
    #                   "in the same orientation/location as the regular input files.  They will be used for "
    #                   "for the 6 parameter alignment. The transformations will then be used to transform "
    #                   "the regular input files, with which the pipeline will continue.")
    group.add_argument("--lsq6-simple", dest="lsq6_method",
                       action="store_const", const="lsq6_simple",
                       help="Run a 6 parameter alignment assuming that the input files are roughly "
                       "aligned: same space, similar orientation. Keep in mind that if you use an "
                       "initial model with both a standard and a native space, the assumption is "
                       "that the input files are already roughly aligned to the native space. "
                       "Three iterations are run: 1st is 17 times stepsize blur, 2nd is 9 times "
                       "stepsize gradient, 3rd is 4 times stepsize blur. [Default = %(default)s]")
    group.add_argument("--lsq6-centre-estimation", dest="lsq6_method",
                       action="store_const", const="lsq6_centre_estimation",
                       help="Run a 6 parameter alignment assuming that the input files have a "
                       "similar orientation, but are scanned in different coils/spaces. [Default = %(default)s]")
    group.add_argument("--lsq6-large-rotations", dest="lsq6_method",
                       action="store_const", const="lsq6_large_rotations",
                       help="Run a 6 parameter alignment assuming that the input files have a random "
                       "orientation and are scanned in different coils/spaces. A brute force search over "
                       "the x,y,z rotation space is performed to find the best 6 parameter alignment. "
                       "[Default = %(default)s]")
    group.add_argument("--lsq6-large-rotations-tmp-dir", dest="large_rotation_tmp_dir",
                       type=str, default="/dev/shm/",
                       help="Specify the directory that rotational_minctracc.py uses for temporary files. "
                       "By default we use /dev/shm/, because this program involves a lot of I/O, and "
                       "this is probably one of the fastest way to provide this. [Default = %(default)s]")
    group.add_argument("--lsq6-large-rotations-parameters", dest="large_rotation_parameters",
                       type=str, default="10,4,10,8",
                       help="Settings for the large rotation alignment. factor=factor based on smallest file "
                       "resolution: 1) blur factor, 2) resample step size factor, 3) registration step size "
                       "factor, 4) w_translations factor  ***** if you are working with mouse brain data "
                       " the defaults do not have to be based on the file resolution; a default set of "
                       " settings works for all mouse brain. In order to use those setting, specify: "
                       "\"mousebrain\" as the argument for this option. ***** [default = %(default)s]")
    group.add_argument("--lsq6-rotational-range", dest="large_rotation_range",
                       type=int, default=50,
                       help="Settings for the rotational range in degrees when running the large rotation "
                       "alignment. [Default = %(default)s]")
    group.add_argument("--lsq6-rotational-interval", dest="large_rotation_interval",
                       type=int, default=10,
                       help="Settings for the rotational interval in degrees when running the large rotation "
                       "alignment. [Default = %(default)s]")
    group.add_argument("--nuc", dest="nuc",
                       action="store_true", 
                       help="Perform non-uniformity correction. [Default = %(default)s]")
    group.add_argument("--no-nuc", dest="nuc",
                       action="store_false", 
                       help="If specified, do not perform non-uniformity correction. Opposite of --nuc.")
    group.add_argument("--inormalize", dest="inormalize",
                       action="store_true", 
                       help="Normalize the intensities after lsq6 alignment and nuc, if done. "
                       "[Default = %(default)s] ")
    group.add_argument("--no-inormalize", dest="inormalize",
                       action="store_false", 
                       help="If specified, do not perform intensity normalization. Opposite of --inormalize.")
    group.add_argument("--copy-header-info-to-average", dest="copy_header_info",
                       action="store_true", 
                       help="Copy the MINC header information of the first input file into the "
                       "average that is created. [Default = %(default)s] ")
    group.add_argument("--no-copy-header-info-to-average", dest="copy_header_info",
                       action="store_false", 
                       help="Opposite of --copy-header-info-to-average.")
    group.add_argument("--lsq6-protocol", dest="lsq6_protocol",
                       type=str, default=None,
                       help="Specify an lsq6 protocol that overrides the default setting for stages in "
                       "the 6 parameter minctracc call. Parameters must be specified as in the following \n"
                       "example: applications_testing/test_data/minctracc_example_linear_protocol.csv \n"
                       "[Default = %(default)s].")

def addStatsArgumentGroup(parser):
    group = parser.add_argument_group("Statistics options", 
                          "Options for calculating statistics.")
    group.add_argument("--stats-kernels", dest="stats_kernels",
                       type=lambda s: ','.split(s), default=[0.5,0.2,0.1],
                       help="comma separated list of blurring kernels for analysis. Default is: 0.5,0.2,0.1")


def addRegistrationChainArgumentGroup(parser):
    group = parser.add_argument_group("Registration chain options",
                        "Options for processing longitudinal data.")
    group.add_argument("--csv-file", dest="csv_file",
                       type=str, required=True,
                       help="The spreadsheet with information about your input data. "
                            "For the registration chain you are required to have the "
                            "following columns in your csv file: \" subject_id\", "
                            "\"timepoint\", and \"filename\". Optionally you can have "
                            "a column called \"is_common\" that indicates that a subject "
                            "is to be used for the common time point using a 1, and 0 "
                            "otherwise.")
    group.add_argument("--common-time-point", dest="common_time_point",
                       type=int, default=None,
                       help="The time point at which the inter-subject registration will be "
                            "performed. I.e., the time point that will link the subjects together. "
                            "If you want to use the last time point from each of your input files, "
                            "(they might differ per input file) specify -1. If the common time "
                            "is not specified, the assumption is that the spreadsheet contains "
                            "the mapping using the \"is_common\" column. [Default = %(default)s]")
    group.add_argument("--common-time-point-name", dest="common_name",
                       type=str, default="common", 
                       help="Option to specify a name for the common time point. This is useful for the "
                            "creation of more readable output file names. Default is \"common\". Note "
                            "that the common time point is the one created by an iterative group-wise " 
                            "registration (inter-subject).")
    group.add_argument("--pride-of-models", dest="pride_of_models",
                       type=str, default=None,
                       help="Specify the top level directory of the \"pride\" of models. "
                       "The idea is that you might want to use different initial models for "
                       "the time points in your data. See our wiki (https://wiki.mouseimaging.ca/) "
                       "for detailed information on the pride of models. [Default = %(default)s]")

