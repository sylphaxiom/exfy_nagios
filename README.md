# check_http_local

The intent of this script is to read a list of servers from a text file, perform a check on each one, then output the
result of that check, raising a WARNING if 1 is down and CRITICAL if both are down.

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

# check_apache

The intent of this script is to view the main Apache log file and parse information out of it. Presently I a only counting
the number of OK responses, 404 errors, and everything else. The script returns the server name, OK status, service name,
and count of entries.

## Dependencies

- Permission changes
  - 755 root nagios /var/log/apache2/
  - 660 root nagios /var/log/apache2/<logFileName>

Please note that it is necessary to update the group and permissions in the apache log rotation config located at
/etc/logrotate.d/apache2. You will need to edit the line that starts with "create" in order for this to be persistent.

Python venv is also required for management of modules. argparse and apachelogs are not standard python libraries and will
need to be installed via pip which warns against system level installations of modules due to conflicts with the OS updater.

### Modules

Script includes imports at the top containing: pprint, logging, argparse, os, subprocess, apachelogs
pdb was used for debugging during development but removed once a branch is merged to main.

### Command line

This script was never intended to be ran by a human being. It is written as a Nagios plugin for server monitoring. Because
of this, I have made a few choices that are seen as "bad practice". I have skipped various steps of error handling because
I am going to assume that the implementation will be configured correctly and there should be no incorrect inputs (if the
installer followed the documentation). The command line on this script is simple, it takes 1 argument (`-f or -file`) for
the name of the apache log to be parsed, and an optional argument (`-p or -path`) to set path of your log file, if different
from the standard /var/log/apache2/

The file argument take a string which is expected to be a file name such as `custom_apache.log` or one of the other `.log`
files. This parameter is required and will throw an error if it is missing.

The path argument is optional. If you do not provide a path, the default path of /var/log/apache2/ will be used during script
execution.

## Functionality

This script was built as a single unit, not broken into functions. This was not by design, but out of convenience as the script
grew in complexity and length. The script will locate the apache log with the filename (and path if provided) provided in the
command. The script pulls the provided information and attempts to validate the path. The path is checked for symlinks and a
warning is given if the provided path is found to be a symlink. After validation the script opens the log file and goes line
by line extracting extracting the information in each line of the log. The assumption is made that the log format is the "combined"
log output (i.e. `LogFormat "%h (orig: %{X-Forwarded-For}i) %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" combined`).

As the script goes line by line, it is organizing the output based on the originating host and the return code of the request.
The script discards communications between Nagios and the server but increments the count of 200 responses. It locates any 404
errors found and incremements that counter and adds the request content as a string to a dictionary containing
`{timestamp : ip+request}`. It next locates all the remaining status codes that are not 200 or 404 and puts them into a dictionary
containing `{timestamp+E+status : request}`. The original intent was to include the data in these dictionaries. This idea was discarded
after testing proved to give too much information and should be implemented a different way. It is common practice to use multiple
levels of verbosity in plugin output, so perhaps that is a place to use this data. For now, it is obtained and not used.

The script will then compose the string value that is being passed to Nagios. Nagios is looking for a specific format of response:
`<host_name>;<svc_description>;<return_code>;<plugin_output>` where the `host_name` and `svc_description` as exactly as defined
in Nagios. This string is then sent to Nagios via `send_nsca` plugin to be registered by nagios.

The script it NOT intended to update the host status. The string that it returns will always show an 'OK' response since it is only
informational.

- Please note the `%{X-Forwarded-For}i` variable was added due to IP forwarding requirements via the load balancer. This is specific
  to our instance and may not be present in your implementation of apache.
