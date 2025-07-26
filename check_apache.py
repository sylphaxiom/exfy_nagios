#!/usr/bin/env python3

"""
    This script is intended to parse apache logs for anything that might be
    concerning. Right now, I'm just going to have it check for 404 errors.
    This is mostly because I find it interesting to see the random things
    that show up in a log. You can see the little processes out there that
    scrape things and prod things on the web. Little catches that could be
    potential security probes. The objective is:
    
    - Parse apache logs for 404 error
    - give a warning if an external IP attmepts to send a request.
    - Send a simple output to NSCA to report to Nagios
    - This is more proof of concept than useful check
    
    If this were a real-world scenario, I would ideally have a better idea
    of what I am supposed to be checking for. Also, I would have an actual
    site with actual analysis. I don't think I have the time to put up a 
    worth-while site at the moment. 

    Dependencies:
    - Add user running script to 'adm' group to view log files
    - touch /var/log/check_apache.log
    - chmod 666 /var/log/check_apache.log
    - python modules: apachelogs, logging, argparse, os, pprint
"""

#import pdb; pdb.set_trace()
from pprint import pprint, pformat
import logging
import argparse
import os
import subprocess
import apachelogs as al

log = logging.getLogger(__name__)
# Adding the default log location so it doesn't log to current directory.
handler = logging.FileHandler('/var/log/check_apache.log')
log.addHandler(handler)
FORMAT = '%(created)f - %(levelname)s: %(message)s'
logging.basicConfig(encoding='utf-8', level=logging.DEBUG, format=FORMAT)
log.info("====================Logging has begun====================")

"""
    There are 2 arguments passed to this script from the command line:
    File (String) - name of the log file (i.e. access.log, error.log)
    Path (String) [optional] - full path to the log file. Default: /var/log/apache2/
"""

parser = argparse.ArgumentParser(
    prog='nagios_apache_check',
    add_help=False, # omitted due to no human useage
    allow_abbrev=True 
)
parser.add_argument('-file', required=True, type=str)
parser.add_argument('-path', required=False, type=str)
args = parser.parse_args() # Namespace(file,path)
log.debug('Raw arguments: %s', args)
# Assign args and validate

if args.file is None:
    log.critical("ERROR - File parameter is required and no value was provided: %s", pformat(args.file))
    raise ValueError('ERROR - File parameter is required. Please provide a value for -file.')
else:
    file = str(args.file)
if args.path is None:
    path = '/var/log/apache2/'
else:
    path = str(args.path)
    # check for training '/'
    log.info("Checking for trailing / now...%s", path)
    if not path.endswith('/'):
        log.info("Oops! You forgot the training /, I got you boo, adding...")
        path = path + '/'
    log.info("Checking validity of the path: %s", path)
    if os.path.isdir(path):
        log.debug("Path is a valid Dir")
        if os.path.islink(path):
            log.warning("WARNING - Path provided is a Symlink. Use caution with this! It could be a security issue")
            log.info("The path you entered was found to be a Symlink. Please use caution.")
        logPath = path + file
        if os.path.isfile(logPath):
            log.info("Path is a vlid file. Path has been validated, continuing script...")
            log.debug("Path tested valid, value: %s", logPath)
        else:
            log.critical("ERROR - The file and path combination you provided is not a valid file, please try again")
            log.critical("ERROR - Vars - path: %s | file: %s | logPath: %s", path, file, logPath)
            raise ValueError('ERROR - Invalid filePath received: %s. Please correct and retry.', logPath)
    else:
        log.critical("ERROR - The path provided is not a valid directory, please try again")
        log.critical("ERROR - Vars - path: %s | file: %s", path, file)
        raise ValueError('ERROR - Invalid filePath received: %s. Please correct and retry.', path)
logPath = path + file 
log.debug("Path should be ready now. logPath var: %s", logPath)

# Now that we have a valid path, let's parse this thing and do stuff with it.
"""
    Set log format according to apache conf file. This is the translation from apachelogs:
    
    LogFormat "%h (orig: %{X-Forwarded-For}i) %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" combined

    %h 					= $.remote_host
    %{X-Forwarded-For}i	= $.headers_in["X-Forwarded-For"]
    %l					= $.remote_logname
    %u					= $.request_url
    %t					= $.request_time_fields["timestamp"]
    %r					= $.request_line
    %>s					= $.final_status
    %O					= $.bytes_out
    %{Referer}i			= $.headers_in["Referer"]
    %{User-Agent}i		= $.headers_in["User-Agent"]
"""
FORMAT = "%h (orig: %{X-Forwarded-For}i) %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\""
parser = al.LogParser(FORMAT)

# Loop throught the file and pull the info you want.
# For right now, I'm pulling a very simple search for 404 and then what was requested.
# This gets returned and sent to Nagios as a passive check on apache.
c200 = 0
c404 = 0
cWARN = 0
flag = 0
logStart = ''
e404 = {}
warnings = {} # dict of timestamp : ip values for external IPs
with open(logPath, 'r') as lf:
    log.info("Opening and beginning parse of log file at %s...", logPath)
    for entry in parser.parse_lines(lf):
        # Now we parse each line with stuff and put it places
        if flag == 0:
            logStart = str(entry.request_time_fields["timestamp"])
            flag += 1
        # Grab vars from the entry
        timestamp = str((entry.request_time_fields["timestamp"]).timestamp())
        dateTime = str(entry.request_time_fields["timestamp"])
        status = entry.final_status
        request = entry.request_line
        # Grab IP
        match entry.remote_host:
            case '172.30.0.244':
                log.debug("Ignore Nagios requests")
                c200 += 1
                continue
            case '172.30.0.130':
                log.debug("Keep stuff from LB and add correct IP")
                ip = str(entry.headers_in["X-Forwarded-For"])
            case _:
                ip = str(entry.request_time_fields["timestamp"])
                log.debug("External IP direct request to web server")
                log.warning("WARNING - External IP found. This server should not be receiving direct requests. Originating IP: %s", entry.remote_host)
                warnings.update({timestamp+ip:'Direct Hit'})
                cWARN += 1
        log.debug("entry IP is: %s", ip)
        match status:
            case 200:
                log.debug("Throwing away OK entries")
                c200 += 1
                continue
            case 404:
                log.debug("404 found, processing...")
                e404.update({timestamp:ip+' - '+request})
                c404 += 1
            case _:
                log.debug("Another status besides 404 and 200 was found: %s", status)
                warnings.update({timestamp+'E'+status:request})
                cWARN += 1
        log.info("Finished parsing the line")
    log.info("Finished working with the logs")
log.info("Information parsed, now to send to Nagios host.")

# Gather data and form the output string

nHost = '172.30.0.244'
svcD404 = '404 errors'
msg404 = 'count-'+c404+'-values-'+e404.values()
svcDwarn = 'Other Returns'
msgWarn = 'count-'+cWARN+'-value-'+str(warnings)
svcDc200 = 'Count of OK Responses'
msg200 = 'count='+c200
stat = 0        # this is informational, not changing state
delim = "\';\'"
sep = "\'|\'"
var = subprocess.run(['hostname'],stdout=subprocess.PIPE)
hName = str(var.stdout).split('.')[0].split('\'')[1]
match hName:
    case 'Sylphaxiom1':
        lHost = 'exfy_1'
    case 'Sylphaxiom2':
        lHost = 'exfy_2'
    case 'Sylphaxiom3':
        lHost = 'exfy_LB'
    case _:
        log.error('ERROR - Hostname did not properly resolve. Please check value: %s', hName)
        raise ValueError('ERROR - Hostname did not resolve, please see log for details.')
log.debug('After match lHost is: %s', lHost)
out404 = lHost+';'+svcD404+';'+stat+';'+msg404
outWarn = lHost+';'+svcDwarn+';'+stat+';'+msgWarn
out200 = lHost+';'+svcDc200+';'+stat+';'+msg200
log.debug('command output:\n\t%s\n\t%s\n\t%s', out200, out404, outWarn)
outCMD = out200+'|'+out404+'|'+outWarn
log.debug('Final command message: %s', outCMD)
log.info('Logs parsed and ready for sending...')
result = subprocess.run(['/usr/local/nagios/bin/send_nsca', '-d', delim, '-e', sep, outCMD], stdout=subprocess.PIPE)
if result == 0:
    log.info('Command successfully sent to Nagios! Exiting...')
else:
    log.critical('ERROR - An unknown error occurred and the command was not successful: %s', result)
    log.info('The command was NOT successful, sorry about that. Check your logs.')
log.debug('Here is the output of the command execution: %s', result.stdout)