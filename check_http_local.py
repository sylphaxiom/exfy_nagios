#!/usr/bin/env python3

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

#import pdb; pdb.set_trace()
from pprint import pprint
import logging
import argparse
import requests
import os

log = logging.getLogger(__name__)
FORMAT = '%(created)f - %(levelname)s: %(message)s'
logging.basicConfig(filename='check_http_local.log', encoding='utf-8', level=logging.WARNING, format=FORMAT)
log.info("====================Logging has begun====================")

"""
There are 2 arguments passed to this script from the command line:
File path (String) [optional]
Log Level (0-5 or NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL) [optional]
"""

parser = argparse.ArgumentParser(
    prog='nagios_http_check',
    add_help=False, # omitted due to no human useage
    allow_abbrev=True 
)
parser.add_argument('-path', required=False, type=str)
parser.add_argument('-log', required=False, type=int, choices=[0,1,2,3,4,5])
args = parser.parse_args() # Namespace(path,log)
log.debug('Raw arguments: %s', args)
logLevel = args.log # If not set, will show as None same with srvPath 
log.info('Log level set as: %s', logLevel)
# if the path is local, empty string, or None, simply use "servers.txt"
srvPath = "servers.txt" if (args.path in ['','./',None]) else  (str(args.path) + "servers.txt")
log.info('srvPath set as: %s', srvPath)

# Documentation says no symlinks. This checks for symlinks and raises an error if found.
if os.path.islink(srvPath):
    log.critical("Symlink was used for servers.txt path. This is a no-no. Please use a real path. Path is: %s", srvPath)
    raise ValueError("WARNING! Using symlinks is not allowed, please only use real file path")
servers = []

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
        log.info('No log level supplied. Default level is 1-DEBUG')

# Open the server file, read contents, add to servers{} 
def getServers(srvPath):
    log.info('Beginning aquisition of server list...')
    rows = []
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
        serv = {}
        cutter = row.split(':', maxsplit=1)
        log.debug('First split to alias: %s | ip: %s', cutter[0], cutter[1])
        log.debug('Final cutter: %s', cutter)
        serv.update({
            'alias':cutter[0],
            'ip':cutter[1]
            })
        log.debug('Final server object: %s', serv)
        servers.append(serv.copy())
    log.info('Parsed servers: %s', pprint(servers))
    return servers

def sendHttp(servers):
    numServ = len(servers)
    log.info('%s servers parsed from server file. Proceeding with HTTP requests...', numServ)
    servLocal = servers.copy()
    servResp = {}
    log.debug('servLocal starting contents: %s', servLocal)
    for serv in servLocal:
        current = serv['alias']
        ip = str(serv['ip'])
        try:
            rq = requests.get('http://'+ip)
            log.debug('request text: %s', rq)
            rq.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error('HTTP error occurred: %s', e)
            errStatus = 'E-' + str(rq.status_code)
            log.debug('errStatus is: %s', errStatus)
            servResp.update({current : errStatus})
            continue
        except requests.exceptions.ConnectionError as e:
            log.error('A connection failed to establish: %s', e)
            errStatus = 'E-FConn'
            log.debug('errStatus is: %s', errStatus)
            servResp.update({current : errStatus})
            continue
        except requests.exceptions.Timeout as e:
            log.error('Connection was timed out: %s', e)
            errStatus = 'E-FTime'
            log.debug('errStatus is: %s', errStatus)
            servResp.update({current : errStatus})
            continue
        except requests.exceptions.RequestException as e:
            log.error('A request error occurred: %s', e)
            errStatus = 'E-FReq'
            log.debug('errStatus is: %s', errStatus)
            servResp.update({current : errStatus})
            continue
        log.info('Request is successful with code: %s', rq.status_code)
        servResp.update({current : str(rq.status_code)})
    log.debug('Server responses are: %s', pprint(servResp))
    return servResp

# Resolve requests into a response for Nagios
def resolveStatus(responses):
    fails = 0
    data = str()
    log.debug(pprint(responses))
    for key, value in responses.items():
        if 'E-' in value:
            fails += 1
            log.info('current failure count: %s', fails)
        data += ' ' + key + '=' + value
    match fails:
        case 0:
            return 'OK:' + data
        case 1:
            return 'WARNING:' + data
        case 2:
            return 'FAILURE:' + data
        case _:
            return 'UNKNOWN:' + data

# Call the first function to pull the servers.
servers = getServers(srvPath) 
log.debug('servers var after getServers: %s', servers)
responses = sendHttp(servers)
log.debug('responses var after sendHttp: %s', responses)
output = resolveStatus(responses)
log.debug('output var after resolveStatus: %s', output)
print(output)

# Return code logic
eSplit = output.split(':', 1)
ec = eSplit[0]
log.debug('ec value prior to exit %s', ec)
match ec:
    case 'OK':
        exit(0)
    case 'WARNING':
        exit(1)
    case 'FAILURE':
        exit(2)
    case _: # since UNKNOWN is basically a catchall, I used a catchall
        exit(3)
