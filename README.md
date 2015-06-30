`pydpiper` is a set of Python modules that offers programmatic control over pipelines. 

It is very much under active development. 

Classes for building and controling the pipeline can be found in `pydpiper/pipeline.py`.
The location of the pipeline directory must be in the user's `$PYTHONPATH`. 

The code for executing the pipeline can be found in `pipeline_executor.py`.

`pydpiper` supports config files (lowest precedence), environment variables, and command-line flags (highest precedence) in a mostly uniform way via the [ConfigArgParse](https://pypi.python.org/pypi/ConfigArgParse) module.  For examples, see the `config` directory; note that unlike the command line, values in key-value pairs must not be quoted (e.g., `--queue-type=sge`, not `--queue-type='sge'`).  The config file should also be accessible to any remote machines.  You can specify a default configuration file location (e.g., for a site-wide default) with the (otherwise undocumented) environment variable `PYDPIPER_CONFIG_FILE`.

You can use environment variables to override our configuration defaults for the underlying Pyro library, except for
`$PYRO_SERVERTYPE` and `$PYRO_LOGFILE`; in particular, you may wish to change `$PYRO_LOGLEVEL`, since this also controls
the verbosity of some of the application's own logging.  See [the Pyro4 documentation](http://pythonhosted.org//Pyro4/) for more options.

Application modules that utilize the pipeline class definitions are currently in applications folder. These applications may be moved to a separate repository at a later date. 
 
*** *** ***
When your pipeline is running, you can verify the state of your pipeline using the following tool (as of version 1.8):

check_pipeline_status.py uri


