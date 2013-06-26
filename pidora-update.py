#!/usr/bin/env python
# Andrew Oatley-Willis
# Multi-purpose tool written in python for linux
# This script will allow for a single safeguarded process to run: sigul, mash, and rsync to pidora.ca
# It will do a sanity check on everything that is happening and prevent manual errors that could occur
# Every configuration is customizable on the command line with well named options
import optparse
import pysftp
import sys
import urllib2
import getpass
import crypt
import random
import re

class tools:
    def __init__(self):
        # Default configuration values
        sigulhost = "england"
        mashhost = "japan"
        rsynchost = "pidora.ca"
        siguluser = "oatley"
        mashuser = "oatley"
        rsyncuser = "pidorapr"
        mashdir = "/usr/local/bin/mash-pidora"
        kojitags = ['f18-updates', 'f18-rpfr-updates', 'f18-updates-testing', 'f18-rpfr-updates-testing']

        # Create command line options
        parser = optparse.OptionParser()
        parser = optparse.OptionParser(usage='Usage: %prog [options]')
        parser.add_option('--status',  help='check the status of all machine', dest='status', default=False, action='store_true')
        parser.add_option('-a', '--all',  help='sign, mash, rsync', dest='all', default=False, action='store_true')
        parser.add_option('-s', '--sign',  help='sign all packages in listed tag', dest='sign', default=False, action='store_true')
        parser.add_option('-m', '--mash',  help='start a mash run', dest='mash', default=False, action='store_true')
        parser.add_option('-r', '--rync',  help='perform a rsync of the mash repos', dest='rsync', default=False, action='store_true')
        parser.add_option('-l', '--list-unsigned',  help='list unsigned rpms', dest='listunsigned', default=False, action='store_true')
        parser.add_option('--koji-tag',  help='specify the koji tag to sign', dest='kojitag', default=False, action='store')
        parser.add_option('--sigul-user',  help='specify the user for sigul', dest='siguluser', default=siguluser, action='store', metavar=siguluser)
        parser.add_option('--sigul-host',  help='specify the host for sigul', dest='sigulhost', default=sigulhost, action='store', metavar=sigulhost)
        parser.add_option('--mash-user',  help='specify the user for mash', dest='mashuser', default=mashuser, action='store', metavar=mashuser)
        parser.add_option('--mash-host',  help='specify the host for mash', dest='mashhost', default=mashhost, action='store', metavar=mashhost)
        parser.add_option('--rsync-user',  help='specify the user for rsync', dest='rsyncuser', default=rsyncuser, action='store', metavar=rsyncuser)
        parser.add_option('--rsync-host',  help='specify the host for rsync', dest='rsynchost', default=rsynchost, action='store', metavar=rsynchost)
        (opts, args) = parser.parse_args()

        # Check number of arguments and check for option switches
        if len(sys.argv[1:]) == 0:
            parser.print_help()
            exit(-1)
        if opts.kojitag:
            kojitags = [opts.kojitag]
        if opts.sigulhost:
            sigulhost = opts.sigulhost
        if opts.mashhost:
            mashhost = opts.mashhost
        if opts.rsynchost:
            rsynchost = opts.rsynchost
        if opts.siguluser:
            siguluser = opts.siguluser
        if opts.mashuser:
            mashuser = opts.mashuser
        if opts.rsyncuser:
            rsyncuser = opts.rsyncuser

        # Create lists of successful and failed hosts
        mhosts, mfail = self.get_status(mashhost, mashuser)
        shosts, sfail = self.get_status(sigulhost, siguluser)
        rhosts, rfail = self.get_status(rsynchost, rsyncuser)
        hosts = mhosts + shosts + rhosts
        fhosts = mfail + sfail + rfail
       
        # Start the main tasks
        if opts.status:
            print 'success: ', hosts 
            print 'failed: ', fhosts 
            exit(0)
        elif sigulhost not in hosts: # Check connection with sigul host
            print 'Cannot connect to sigul: failed hosts: ', fhosts
            exit(1)
        elif opts.listunsigned:
            for tag in kojitags:
                print 'Unsigned packages: ' + tag
                self.checksign(sigulhost, siguluser, tag)
            exit(0)
        elif opts.sign:
            self.run_sign(sigulhost, siguluser, kojitags)
            exit(0)
        elif mashhost not in hosts: # Check connection with mash host
            print 'Cannot connect to mash hosts: failed hosts: ', fhosts
            exit(1)
        elif opts.mash:
            self.run_mash(mashhost, mashuser, kojitags)
            exit(0)
        elif rsynchost not in hosts: # Check connection with rsync host
            print 'Cannot connect to rsync hosts: failed hosts: ', fhosts
            exit(1)
        elif opts.rsync:
            self.rsync(rsynchost, rsyncuser)
            exit(0)
        elif opts.everything:
            self.run_sign(sigulhost, siguluser, kojitags)
            self.run_mash(mashhost, mashuser, kojitags)
            self.rsync(rsynchost, rsyncuser)
            exit(0)
    
    # Call sign over multiple koji tags and ask only once for the password
    def run_sign(sigulhost, siguluser, kojitags):
        print '\nEnter sigul key passphrase to sign these packages:'
        password = getpass.getpass()
        for tag in kojitags:
            self.sign(sigulhost, siguluser, tag, password)
            print ""

    # Call mash and check that all packages are signed
    def run_mash(mashhost, mashuser, kojitags):
        for tag in kojitags: # Check for unsigned packages before mashing
            if self.checksign(sigulhost, siguluser, tag):
                print 'Cannot mash while packages are unsigned: '
                self.checksign(sigulhost, siguluser, tag)
                exit(1)
        self.mash(mashhost, mashuser)

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
    def sign(self, host, username, tag, password):
        print "Signing packages in tag: " + tag
        print "Packages found: "
        print self.checksign(host, username, tag)
        tempfile1 = crypt.crypt(str(random.random()), "pidora" ) + '.log'
        tempfile = tempfile1.replace("/", "")
        tempdir = '~/.pidora/'
        srv = pysftp.Connection(host=host, username=username, log=True)
        errors = srv.execute('mkdir ' + tempdir + ' 2>/dev/null')
        errors = srv.execute('touch ' + tempdir + tempfile + '2>/dev/null')
        output = srv.execute('~/.sigul/sigulsign_unsigned.py -v --password=' + password + ' --write-all --tag=' + tag + " pidora-18 2>" + tempdir + tempfile)
        errors = srv.execute('cat ' + tempdir + tempfile)
        srv.close()
        # Scan through output and find errors! If errors are found, stop program and spit out error warnings
        outputs = output + errors
        errors = False
        for output in outputs:
            print output.strip()
            if re.search('^ERROR:.*$', output):
                errors = True
        if errors:
            print "\n== Error signing stopping program =="
            exit(1)

    # Check koji for unsigned packages, returns True if unsigned rpms are found
    def checksign(self, host, username, tag):
        check = False
        srv = pysftp.Connection(host=host, username=username, log=True)
        output = srv.execute("~/.sigul/sigulsign_unsigned.py --just-list --tag=" + tag + " pidora-18")
        srv.close()
        for rpm in output:
            print rpm.strip()
            if rpm.strip() != "":
                check = "unsigned rpms found"
        if check:
            return True

    # Run mash and search through the log file for failed mash errors
    def mash(self, host, username):
        errors = False
        errorline = []
        srv = pysftp.Connection(host=host, username=username, log=True)
        output = srv.execute('/usr/local/bin/pidora-mash-run')
        output = srv.execute('cat /mnt/koji/mash/pidora-mash-latest')
        srv.close()
        for line in lines:
            if re.search('^mash failed .*$', line):
                errorline.append(line.strip())
                errors = True
        if errors:
            print "\n== mash failed on repo stopping program ==\n"
            for line in errorline:
                print line
            exit(1)

    def rsync(self, host, username):
        srv = pysftp.Connection(host=host, username=username, log=True)
        output = srv.execute('/home/pidorapr/bin/rsync-japan')
        srv.close()
        for line in output:
            print line.strip()

if __name__ == '__main__':
    tools()
