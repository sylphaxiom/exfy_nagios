# exfy_nagios

The intent of this repo is as a source control and method of deployment for coding Nagios plugins with Python.

## Dependencies

### servers.txt

This script relies on a `.txt` file containing a list of servers in the format `<alias>:<ip>` with each on it's own line.
You can add comments to this file by adding a `#` at the beginning of a line. The script will slice on the `:` character
and using the `<alias>` as the server name and the `<ip>` to send an HTTP request.

### Modules

Script includes imports at the top containing: pprint, logging, argparse, requests
pdb was used for debugging during development but removed once a branch is merged to main.

### Command line

This script was never intended to be ran by a human being. It is written as a Nagios plugin for server monitoring. Because
of this, I have made a few choices that are seen as "bad practice". I have skipped various steps of error handling because
I am going to assume that the implementation will be configured correctly and there should be no incorrect inputs (if the
installer followed the documentation). The command line on this script is simple, it takes 1 argument (`-p or -path`) for the path
of the `servers.txt` file, and an argument (`-l or -log`) to set the log level. Both are optional

The path argument is a simple string representing a unix path. The script assumes a path of `./` to mean this directory and
uses `'servers.txt'` instead of `'./servers.txt'`. All other paths have `'servers.txt'` appended to the end of the input path.
This means you should include the trailing `/` of the path as in `'~/file/directory/'`.

The log level can be one of 6 values: 0-5. They stand for the log levels `NOSET`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
(respectively). The logs will output messages pertaining to the log level or higher that is set in the script. Setting `-log 3`
will set the level to `WARNING`. This means you will only see `WARNING`, `ERROR`, and `CRITICAL` messages.

## Functionality

### check_http_local.py

This is the main script. 3 functions are dfined and then called in sequence passing their information to eachother resulting
in a single `print()` statement to print to `STOUT` for Nagios. The script is intended to be ran by calling the script from the command
line. There are 2 args which are both optional `-p or -path` and `-l or -log`. If neither are provided it is assumed the `servers.txt`
file is located in the same directory as the script and that the log level is `3-WARNING`. Above the definitions of the following
functions, is the start of logging and assignment of arguments.

### getServers(String srvPath): returns List servers

This function accepts a string which is assumed to be a path to the servers.txt file. If this argument is missing, the filename
is used and it is assumed to be in the same directory as the parent script. This function splits reads the contents of `servers.txt`
and parses each line. Any lines begnning with `#` are ignored. The uncommented lines are assumed to be of the format `<alias>:<ip>`.
They are sliced at the `:` and used as the alias and IP for the next functions. This function returns a list of servers.

### sendHTTP(List servers): returns Dict servResp

This function accespts the list of servers pulled from the `servers.txt` file. It uses the loops through each server dict and uses
the `ip` to send a short http request. It then takes the response and looks at the `status_code` to determine success or failure.
Using `requests.status_code` we try/except for error responses and mark them as failures, appending `E-` to the beginning of the
status code. The server alias and status codes are combined into a dict and returned from the function.

### resolveStatus(Dict servResp): returns String output

This function takes the return codes supplied from the previous function and determines a simple string response to print to Nagios.
The response is in the form of `SERVICE STATUS: <alias>=<status_code> <alias2>=<status_code2>...` The `SERVICE STATUS` is one of 4
values:

- `OK` = HTTP request returned an acceptable response code
- `WARNING` = 1 server has failed
- `FAILURE` = 2 servers have failed
- `UNKNOWN` = more than 2 servers failed or other error
  This output is printed to `STDOUT` at the conclusion of the script.
