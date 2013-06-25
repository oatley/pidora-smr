#!/usr/bin/env python
# Multi-purpose tool written in python for linux

import optparse
import pysftp
import sys
import urllib2

class tools:
    def __init__(self):
        sigulhost = "england"
        mashhost = "japan"
        mashdir = "/usr/local/bin/mash-pidora"
        username = "oatley"
        hosts = ['fail', 'scotland', sigulhost, mashhost]
        parser = optparse.OptionParser()
        parser.add_option('-s', '--status',  help='check the status of all machine', dest='status', default=False, action='store_true')
        parser.add_option('-k', '--koji-tag',  help='specify the koji tag to use in the sign', dest='kojitag', default=False, action='store')
        parser.add_option('-u', '--sigul',  help='specify the koji tag to use in the sign', dest='kojitag', default=False, action='store')
        (opts, args) = parser.parse_args()
        # Check number of arguments 
        if len(sys.argv[1:]) == 0:
            parser.print_help()
            exit(-1)
        # Create lists of successful and failed hosts
        shosts, fhosts = self.get_status(hosts, username)
        if opts.status:
            print 'success: ', shosts 
            print 'fail: ', fhosts
            exit(0)
        if opts.kojitag:
            print 'using koji tag ' + opts.kojitag



    # Check if hosts are online and can establish connection, return lists of failed and succesful hosts
    def get_status(self, hosts, username):
        shosts = [] # Successful hosts
        fhosts = [] # Failed hosts
        for host in hosts:
            output = self.status(host, username)
            if output:
                shosts.append(host)
            else:
                fhosts.append(host)
        return (shosts, fhosts)

    def status(self, host, username):
        try:
            response=urllib2.urlopen('http://'+host,timeout=1)
            srv = pysftp.Connection(host=host, username=username, log=True)
            srv.close()
            return True
        except urllib2.URLError as err:pass
        except:pass
        return False

if __name__ == '__main__':
    tools()
