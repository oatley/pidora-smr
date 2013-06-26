#!/usr/bin/env python
# Multi-purpose tool written in python for linux
# This script will allow for a single safeguarded process to run: sigulsign_unsigned, mash-pidora, and rsync to pidora.ca
# It will do a sanity check on everything that is happening and hopefully prevent manual errors that could occur
# Because I'm running subprocess here, now this script can only be run by root on japan
import optparse
import pysftp
import sys
import urllib2

class tools:
    def __init__(self):
        sigulhost = "england.proximity.on.ca"
        mashhost = "japan.proximity.on.ca"
        mashdir = "/usr/local/bin/mash-pidora"
        mashuser = ""
        siguluser = "oatley"
        parser = optparse.OptionParser()
        parser = optparse.OptionParser(usage='Usage: %prog [options]')
        parser.add_option('--status',  help='check the status of all machine', dest='status', default=False, action='store_true')
        parser.add_option('-a', '--all',  help='sign, mash, rsync', dest='all', default=False, action='store_true')
        parser.add_option('-s', '--sign',  help='sign, mash, rsync', dest='all', default=False, action='store_true')
        parser.add_option('-m', '--mash',  help='sign, mash, rsync', dest='all', default=False, action='store_true')
        parser.add_option('-r', '--rync',  help='sign, mash, rsync', dest='all', default=False, action='store_true')
        parser.add_option('--koji-tag',  help='specify the koji tag to sign', dest='kojitag', default=False, action='store')
        parser.add_option('--sigul-user',  help='specify the user to use for sigul', dest='siguluser', default=False, action='store')
        parser.add_option('--sigul-host',  help='specify the host for sigul', dest='sigulhost', default=sigulhost, action='store', metavar=sigulhost)
        parser.add_option('--mash-user',  help='specify the user for mash', dest='mashuser', default='root', action='store', metavar='root')
        parser.add_option('--mash-host',  help='specify the host for mash', dest='mashhost', default=mashhost, action='store', metavar=mashhost)
        (opts, args) = parser.parse_args()
        # Check number of arguments 
        if len(sys.argv[1:]) == 0:
            parser.print_help()
            exit(-1)
        if opts.kojitag:
            kojitag = opts.kojitag
        if opts.siguluser:
            siguluser = opts.siguluser
        if opts.mashuser:
            mashuser = opts.mashuser

        # Create lists of successful and failed hosts
        mhosts, mfail = self.get_status(mashhost, mashuser)
        shosts, sfail = self.get_status(sigulhost, siguluser)
        hosts = mhosts + shosts
        fhosts = mfail + sfail
        
        if opts.status:
            print 'success: ', hosts 
            exit(0)
        if sigulhost not in hosts or mashhost not in hosts:
            print 'Cannot connect to hosts: ', fhosts
            exit(1)


    # Check if hosts are online and can establish connection, return lists of failed and succesful hosts
    def get_status(self, host, username):
        hostname = []
        fhost = []
        check = self.connect(host, username)
        if check:
            hostname.append(host)
        else:
            fhost.append(host)
        return (hostname, fhost)
    
    # Connect to the hosts, return True or False
    def connect(self, host, username):
        try:
            response=urllib2.urlopen('http://'+host,timeout=1)
            srv = pysftp.Connection(host=host, username=username, log=True)
            srv.close()
            return True
        except urllib2.URLError as err:pass
        except:pass
        return False

    # Start a signing run across a designated tag
    def sign(self, host, username, tag):
        srv = pysftp.Connection(host=host, username=username, log=True)
        output = srv.execute("~/.sigul/sigulsign_unsigned.py -v --write-all --tag=" + tag + " pidora-18")
        srv.close()
        # Scan through output and find errors! If errors are found, stop program and spit out error warnings
        if 'Error' in output or 'error' in output:
            print 'Errors detected'
            return False
        return True

    # Check koji for unsigned packages, do not continue if unsigned packages are found
    # Maybe remove the -v for parsing
    def checksign(self, host, username):
        srv = pysftp.Connection(host=host, username=username, log=True)
        output = srv.execute("~/.sigul/sigulsign_unsigned.py --just-list --tag=" + tag + " pidora-18")
        srv.close()
        if output:
            print 'The follow rpms are unsigned: ' + output
            return False
        return True

    # Because I'm running subprocess here, now this script can only be run by root on japan
    def mash(self):
        output = subprocess.check_output(['/usr/local/bin/pidora-mash-run'], shell=True)
        return output

if __name__ == '__main__':
    tools()












