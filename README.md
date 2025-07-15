# exfy_nagios

The intent of this repo is as a source control and method of deployment for coding Nagios plugins with Python.

## Dependencies

### servers.txt

This script relies on a `.txt` file containing a list of servers in the format <alias>:<ip> with each on it's own line.
You can add comments to this file by adding a `#` at the beginning of a line. The script will slice on the `:` character
and using the <alias> as the server name and the <ip> to send an HTTP request.

### Modules

Script includes imports at the top containing: pprint, logging, argparse, requests
pdb was used for debugging during development but removed once a branch is merged to main.

### Command line

This script was never intended to be ran by a human being. It is written as a Nagios plugin for server monitoring. Because
of this, I have made a few choices that are seen as "bad practice". I have skipped various steps of error handling because
I am going to assume that the implementation will be configured correctly and there should be no incorrect inputs (if the
installer followed the documentation). The command line on this script is simple, it takes 1 positional argument for the path
of the servers.txt file, and it takes an optional (-l or -log) parameter to set the log level.

The path argument is a simple string representing a unix path. The script assumes a path of `./` to mean this directory and
uses `'servers.txt'` instead of `'./servers.txt'`. All other paths have `'servers.txt'` appended to the end of the input path.
This means you should include the trailing `/` of the path as in `'~/file/directory/'`.

The log level can be one of 6 values: 0-5. They stand for the log levels NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
(respectively). The logs will output messages pertaining to the log level or higher that is set in the script. Setting `-log 3`
will set the level to WARNING. This means you will only see WARNING, ERROR, and CRITICAL messages.
