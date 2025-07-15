""" Script is intended to read in a list of servers from a file
    and then run a simple check on those servers by sending a
    simple HTTP request to them and observing the result.
    Basic outline:
    srv_read()
        opens file, creates server list
    http_req(server)
        Compiles the request, sends, analyzes response
    parse_health(response)
        handles conveying data from response to Nagios
    
    Since this is going to be ran by Nagios and is not intended
    to be ran by humans alone, I will make the assumption that the
    arguments will ALWAYS be passed to the script as intended.
    I understand this is bad practice for human interactive
    scripts, but that is my justification for this choice.
"""

import pdb; pdb.set_trace()

import sys
import logging
import argparse

log = logging.getLogger(__name__)
logging.basicConfig(filename='check_http_local.log', encoding='utf-8', level=logging.DEBUG)
log.info("====================Logging has begun====================")

# Global scoped vars and defs

"""
There are 2 arguments passed to this script from the command line:
File path (String)
Log Level (0-5 or NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL) [optional]
"""

parser = argparse.ArgumentParser(
    prog='nagios_http_check',
    add_help=False, # omitted due to no human useage
    allow_abbrev=True 
)
parser.add_argument('path')
parser.add_argument('-log', required=False, type=int, choices=[0,1,2,3,4,5])
args = parser.parse_args()
log.debug('Raw arguments: %s', args)
logLevel = args.log
log.info('Log level set as: %s', logLevel)
srvPath = "servers.txt" if (args.path =='./') else  args.path + "servers.txt"
log.info('srvPath set as: %s', srvPath)
servers = {}

# If a log level is passed to the program, update level
match logLevel:
    case 0:
        logging.getLogger(__name__).setLevel(logging.NOTSET)
        log.info('Log level set to %s', '0-NOTSET')
    case 1:
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        log.info('Log level set to %s', '1-DEBUG')
    case 2:
        logging.getLogger(__name__).setLevel(logging.INFO)
        log.info('Log level set to %s', '2-INFO')
    case 3:
        logging.getLogger(__name__).setLevel(logging.WARNING)
        log.info('Log level set to %s', '3-WARNING')
    case 4:
        logging.getLogger(__name__).setLevel(logging.ERROR)
        log.info('Log level set to %s', '4-ERROR')
    case 5:
        logging.getLogger(__name__).setLevel(logging.CRITICAL)
        log.info('Log level set to %s', '5-CRITICAL')
    case _:
        log.info('No log level supplied. Default level is 3-WARNING')

# Open the server file, read contents, add to servers{} 
def getServers(srvPath):
    log.info('Beginning aquisition of server list...')
    rows = []
    serv={}
    with open(srvPath, "r") as file:
        for line in file:
            line = line.strip('\n') # Sanitize the line of breaks
            log.debug('uncut line from file: %s', line)
            if line[0] == '#':
                log.info('skipping comment: %s', line)
                continue
            rows.append(line)
        log.info('File operations completed, parsing servers...')
    for row in rows:
        cutter = row.split(':', maxsplit=1)
        log.debug('First split to alias: %s | server: %s', cutter[0], cutter[1])
        if '/' in cutter[1]:
            log.info('IP found starting next cutter')
            net = cutter[1].split('/', maxsplit=1)
            log.debug('IP slice: %s', net)
            cutter[1] = net[0]
            serv.update({'ip':net[1]})
        log.debug('Final cutter: %s', cutter)
        serv.update({
            'alias':cutter[0],
            'host':cutter[1]
            })
        log.debug('Final server object: %s', serv)
        servers.update({'server': serv})
    log.info('Parsed servers: %s', servers)
    return servers

# Call the first function to pull the servers.

servers = getServers(srvPath) 
