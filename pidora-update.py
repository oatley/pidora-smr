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
import string
import subprocess
import os

class tools:
    def __init__(self):
        # Default configuration values
        self.sigulhost = "england.proxmity.on.ca"
        self.mashhost = "japan.proximity.on.ca"
        self.rsynchost = "pidora.proximity.on.ca"
        self.siguluser = "agreene"
        self.mashuser = "root"
        self.rsyncuser = "pidorapr"
        self.mashdir = "/usr/local/bin/mash-pidora"
        self.kojitags = ['f18-updates', 'f18-rpfr-updates', 'f18-updates-testing', 'f18-rpfr-updates-testing']
        self.email = "andrew.oatley-willis@senecacollege.ca"
        self.auto = False
        self.logdir = "/var/log/pidora-smr/"
        self.logfile = "output"

        # Create command line options
        parser = optparse.OptionParser()
        parser = optparse.OptionParser(usage='Usage: %prog [options]')
        parser.add_option('-i', '--info',  help='check machine status and configuration', dest='status', default=False, action='store_true')
        parser.add_option('-a', '--all',  help='sign, mash, rsync', dest='everything', default=False, action='store_true')
        parser.add_option('-s', '--sign',  help='sign all packages in listed tag', dest='sign', default=False, action='store_true')
        parser.add_option('-m', '--mash',  help='start a mash run', dest='mash', default=False, action='store_true')
        parser.add_option('-r', '--rsync',  help='perform a rsync of the mash repos', dest='rsync', default=False, action='store_true')
        parser.add_option('-l', '--list-unsigned',  help='list unsigned rpms', dest='listunsigned', default=False, action='store_true')
        parser.add_option('--auto',  help='enables logging and emails logs', dest='auto', default=self.auto, action='store_true')
        parser.add_option('--koji-tag',  help='specify the koji tag to sign', dest='kojitag', default=False, action='store')
        parser.add_option('--email',  help='specify the email to send logs to', dest='email', default=False, action='store', metavar=self.email)
        parser.add_option('--sigul-user',  help='specify the user for sigul', dest='siguluser', default=self.siguluser, action='store', metavar=self.siguluser)
        parser.add_option('--sigul-host',  help='specify the host for sigul', dest='sigulhost', default=self.sigulhost, action='store', metavar=self.sigulhost)
        parser.add_option('--mash-user',  help='specify the user for mash', dest='mashuser', default=self.mashuser, action='store', metavar=self.mashuser)
        parser.add_option('--mash-host',  help='specify the host for mash', dest='mashhost', default=self.mashhost, action='store', metavar=self.mashhost)
        parser.add_option('--rsync-user',  help='specify the user for rsync', dest='rsyncuser', default=self.rsyncuser, action='store', metavar=self.rsyncuser)
        parser.add_option('--rsync-host',  help='specify the host for rsync', dest='rsynchost', default=self.rsynchost, action='store', metavar=self.rsynchost)
        parser.add_option('--log-dir',  help='specify a logging directory', dest='logdir', default=self.logdir, action='store', metavar=self.logdir)
        parser.add_option('--log-file',  help='specify a log file name', dest='logfile', default=self.logfile, action='store', metavar=self.logfile)
        (opts, args) = parser.parse_args()

        # Check number of arguments and check for option switches
        if len(sys.argv[1:]) == 0:
            parser.print_help()
            exit(-1)
        if opts.kojitag:
            self.kojitags = [opts.kojitag]
        if opts.sigulhost:
            self.sigulhost = opts.sigulhost
        if opts.mashhost:
            self.mashhost = opts.mashhost
        if opts.rsynchost:
            self.rsynchost = opts.rsynchost
        if opts.siguluser:
            self.siguluser = opts.siguluser
        if opts.mashuser:
            self.mashuser = opts.mashuser
        if opts.rsyncuser:
            self.rsyncuser = opts.rsyncuser
        if opts.email:
            self.email = opts.email
        if opts.auto:
            self.auto = opts.auto
        if opts.logdir:
            self.logdir = opts.logdir
        if opts.logfile:
            self.logfile = self.logdir + opts.logfile
        
        # Check for a few strange situations with options
        self.signmash = False
        self.signrsync = False
        self.mashrsync = False
        if opts.sign and opts.mash and opts.rsync:
            opts.sign = False
            opts.mash = False
            opts.rsync = False
            opts.everything = True
        elif opts.sign and opts.mash:
            opts.sign = False
            opts.mash = False
            self.signmash = True
        elif opts.sign and opts.rsync:
            opts.sign = False
            opts.rsync = False
            self.signrsync = True
        elif opts.mash and opts.rsync:
            opts.mash = False
            opts.rsync = False
            self.mashrsync = True

        # Create lists of successful and failed hosts
        mhosts, mfail = self.get_status(self.mashhost, self.mashuser)
        shosts, sfail = self.get_status(self.sigulhost, self.siguluser)
        rhosts, rfail = self.get_status(self.rsynchost, self.rsyncuser)
        self.hosts = mhosts + shosts + rhosts
        self.fhosts = mfail + sfail + rfail
       
        # Start the main tasks
        if opts.status:
            print self.info()
        elif self.sigulhost not in self.hosts: # Check connection with sigul host
            self.email_exit('[Error]\nCannot connect to sigul: failed hosts: \n' + self.info(), subject='pidora-smr - failed', errors=1)
        elif opts.listunsigned:
            print 'Unsigned packages: ', self.kojitags
            self.checksign()
            exit(0)
        elif not opts.sign and not opts.mash and not opts.rsync and not opts.everything:
            parser.print_help()
            exit(-1)
        elif opts.sign:
            self.sign()
            self.email_exit('[Success]\nSign for pidora complete', subject='pidora-smr - success')
        elif self.mashhost not in self.hosts: # Check connection with mash host
            self.email_exit('[Error]\nCannot connect to mash: failed hosts: \n' + self.info(), subject='pidora-smr - failed', errors=1)
        elif self.checksign():
            print 'Unsigned packages: ', self.kojitags
            self.checksign()
            print 'Cannot mash or rsync if packages are not signed'
            exit(0)
        elif opts.mash:
            self.mash()
            self.email_exit('[Success]\nMash for pidora complete', subject='pidora-smr - success')
        elif self.rsynchost not in self.hosts: # Check connection with rsync host
            self.email_exit('[Error]\nCannot connect to rsync: failed hosts: \n' + self.info(), subject='pidora-smr - failed', errors=1)
        elif opts.rsync:
            self.rsync()
            self.email_exit('[Success]\nRsync for pidora complete', subject='pidora-smr - success')
        elif opts.everything:
            self.sign()
            self.mash()
            self.rsync()
            self.email_exit('[Success]\nSign, mash, rsync for pidora complete', subject='pidora-smr - success')
   
    # Email text and subject, written a little bit crazy...
    def sendemail(self, subject, text):
        arg = '-s "' + subject + '" "' + self.email + '"'
        output = subprocess.check_output(['echo "' + str(text) + '" |mail ' + str(arg)], shell=True)

    def logging(self, logme):
        try:
            os.mkdirs(directory)
        except OSError: pass

    # Display all configuration data + hosts status
    def info(self, infotype='all'):
        if infotype == 'all':
            info = ['\n[Connection]\nsigulhost = ' + self.sigulhost,
                    'siguluser = ' + self.siguluser,
                    'mashhost = ' + self.mashhost,
                    'mashuser = ' + self.mashuser,
                    'rsynchost = ' + self.rsynchost,
                    'rsyncuser = ' + self.rsyncuser,
                    '\n[General]\nauto = ' + str(self.auto),
                    'mashdir = ' + self.mashdir,
                    'kojitags = ' + str(self.kojitags),
                    'email = ' + self.email,
                    '\nlogdir = ' + self.logdir, 
                    'logfile = ' + self.logfile, 
                    '\n[Hosts]\nworking hosts: ' + str(self.hosts),
                    'failed hosts: ' + str(self.fhosts) + '\n']
        elif infotype == 'sign':
            info = ['\n[Connection]\nsigulhost = ' + self.sigulhost,
                    'siguluser = ' + self.siguluser,
                    '\n[General]\nauto = ' + str(self.auto),
                    'kojitags = ' + str(self.kojitags),
                    'logdir = ' + self.logdir, 
                    'logfile = ' + self.logfile, 
                    '\n[Hosts]\nworking hosts: ' + str(self.hosts),
                    'failed hosts: ' + str(self.fhosts) + '\n']
        elif infotype == 'mash':
            info = ['\n[Connection]\nmashhost = ' + self.mashhost,
                    'mashuser = ' + self.mashuser,
                    '\n[General]\nauto = ' + str(self.auto),
                    'mashdir = ' + self.mashdir,
                    'kojitags = ' + str(self.kojitags),
                    '\nlogdir = ' + self.logdir, 
                    'logfile = ' + self.logfile, 
                    '\n[Hosts]\nworking hosts: ' + str(self.hosts),
                    'failed hosts: ' + str(self.fhosts) + '\n']
        elif infotype == 'rsync':
            info = ['\n[Connection]\nrsynchost = ' + self.rsynchost,
                    'rsyncuser = ' + self.rsyncuser,
                    'mashdir = ' + self.mashdir,
                    '\n[General]\nauto = ' + str(self.auto),
                    'kojitags = ' + str(self.kojitags),
                    '\nlogdir = ' + self.logdir, 
                    'logfile = ' + self.logfile, 
                    '\n[Hosts]\nworking hosts: ' + str(self.hosts),
                    'failed hosts: ' + str(self.fhosts) + '\n']
        return '\n'.join(info)

    # Display text and exit or send an email and exit
    def email_exit(self, text, subject=False, errors=0):
        if self.auto and subject:
            self.sendemail(subject, text)
            exit(errors)
        else:
            print text
            exit(errors)

    # Rsync to the repo directory
    def rsync(self):
        print '\n== Start: Rsync ==\n'
        self.checkmash()
        srv = pysftp.Connection(host=self.rsynchost, username=self.rsyncuser, log=True)
        output = srv.execute('/home/pidorapr/bin/rsync-japan; echo $? > /home/pidorapr/.rsync-japan-exit-status')
        for line in output:
            print line.strip()
        output = srv.execute('cat /home/pidorapr/.rsync-japan-exit-status')
        srv.close()
        if str(output.strip()) != '0':
            self.email_exit('[Error]\nRsync failed stopping program\nExit status = ' + str(output.strip()) + self.info(), subject='pidora-smr - failed', errors=1)



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
    def sign(self):
        print '\n== Start: Sign run ==\n'
        print 'Koji tags marked for signing:'
        for tag in self.kojitags:
            print tag.strip()
        print '\nEnter sigul key passphrase:'
        password = getpass.getpass()
        for tag in self.kojitags:
            print "Signing packages in tag: " + tag
            print "Packages found: "
            print self.checksign()
            tempfile1 = crypt.crypt(str(random.random()), "pidora" ) + '.log'
            tempfile = tempfile1.replace("/", "")
            tempdir = '~/.pidora/'
            srv = pysftp.Connection(host=self.sigulhost, username=self.siguluser, log=True)
            errors = srv.execute('mkdir ' + tempdir + ' 2>/dev/null')
            errors = srv.execute('touch ' + tempdir + tempfile + '2>/dev/null')
            output = srv.execute('~/.sigul/sigulsign_unsigned.py -v --password=' + password + ' --write-all --tag=' + tag + " pidora-18 2>" + tempdir + tempfile)
            errors = srv.execute('cat ' + tempdir + tempfile)
            srv.close()
            # Scan through output and find errors! If errors are found, stop program and spit out error warnings
            outputs = output + errors
            errors = []
            for output in outputs:
                print output.strip()
                if re.search('^ERROR:.*$', output):
                    errors.append(output)
            if errors:
                self.email_exit('[Error]\nError signing stopping program\n' + str(errors) + self.info(), subject='pidora-smr - failed', errors=1)

    # Check koji for unsigned packages, returns True if unsigned rpms are found
    def checksign(self):
        check = False
        for tag in self.kojitags:
            srv = pysftp.Connection(host=self.sigulhost, username=self.siguluser, log=True)
            output = srv.execute("~/.sigul/sigulsign_unsigned.py --just-list --tag=" + tag + " pidora-18")
            srv.close()
            for rpm in output:
                print rpm.strip()
                if rpm.strip() != "":
                    check = "unsigned rpms found"
        if check:
            return True

    # Run mash and search through the log file for failed mash errors
    def mash(self):
        print '\n== Start: Mash run ==\n'
        srv = pysftp.Connection(host=self.mashhost, username=self.mashuser, log=True)
        output = srv.execute('/usr/local/bin/mashrun-pidora-18')
        srv.close()
        self.checkmash()

    def checkmash(self):
        errors = []
        srv = pysftp.Connection(host=self.mashhost, username=self.mashuser, log=True)
        output = srv.execute('cat /mnt/koji/mash/pidora-mash-latest/mash.log')
        srv.close()
        for line in output:
            if re.search('^mash failed .*$', line):
                errors.append(line.strip())
        if errors:
            self.email_exit('[Error]\nmash failed on repo stopping program\n' + str(errors) + self.info(), subject='pidora-smr - failed', errors=1)
            
        

if __name__ == '__main__':
    tools()
