# This software and any associated files are copyright 2010 Brian Carver and
# Michael Lissner.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  Under Sections 7(a) and 7(b) of version 3 of the GNU Affero General Public
#  License, that license is supplemented by the following terms:
#
#  a) You are required to preserve this legal notice and all author
#  attributions in this program and its accompanying documentation.
#
#  b) You are prohibited from misrepresenting the origin of any material
#  within this covered work and you are required to mark in reasonable
#  ways how any modified versions differ from the original version.


import sys
sys.path.append('/var/www/court-listener/alert')

import settings
from django.core.management import setup_environ
setup_environ(settings)

from alert.search.models import Court
from alert.search.models import Citation
from alert.search.models import Document
from lib.db_tools import queryset_iterator

import datetime
import gc
import time

from optparse import OptionParser


def delete_data_by_time_and_court(courtID, SIMULATE, delTime=None, VERBOSITY=0):
    '''
    Deletes data for a court. If a time is given, uses that time as a constraint.
    '''
    if delTime is not None:
        if VERBOSITY >= 1:
            print "Deleting data newer than %s for court %s" % (delTime, courtID)
        count = Document.objects.filter(time_retrieved__gt=delTime, court=courtID).count()
        if count != 0:
            docs = queryset_iterator(Document.objects.filter(time_retrieved__gt=delTime, court=courtID))

    else:
        if VERBOSITY >= 1:
            print "Deleting all data for court %s" % courtID
        count = Document.objects.filter(court=courtID).count()
        if count != 0:
            docs = queryset_iterator(Document.objects.filter(court=courtID))

    if VERBOSITY >= 1:
        print "Deleting %s documents from the database." % (count)
    if (not SIMULATE) and (count != 0):
        for doc in docs:
            doc.delete()



def delete_all_citations(SIMULATE, VERBOSITY=0):
    '''
    Deletes all citations and their associated documents.
    '''
    if VERBOSITY >= 1:
        print "Deleting all citations and associated documents."
    cites = Citation.objects.all()
    if VERBOSITY >= 2:
        print 'Deleting %s citations and documents from the database.' % len(cites)
    if not SIMULATE:
        try:
            input = raw_input('\nPress enter to continue or Ctrl+C to exit. ')
        except KeyboardInterrupt:
            print "\nAborted by user."
            exit(2)
        cites.delete()


def delete_orphaned_citations(SIMULATE, VERBOSITY=0):
    '''
    Deletes all citations that don't have a document associated with them.

    This is brutally inefficient, iterating over ALL citations in the DB, and
    performing one query per citation.
    '''
    if VERBOSITY >= 1:
        print "Deleting all citations that are not associated with a document."
    cites = Citation.objects.all()

    total = 0
    for cite in cites:
        docs = Document.objects.filter(citation=cite)
        if docs.count() == 0:
            if VERBOSITY >= 2:
                print "Deleting orphan citation %s from the database." % cite
            if not SIMULATE:
                cite.delete()
                total += 1
    if VERBOSITY >= 1:
        print "Deleted %s orphaned citations from the database." % total


def main():
    '''Manipulates the database in convenient ways.

    This script has some basic commands that allow manipulations of the database
    in somewhat more convenient ways than provided through other utilities.

    Yes, it's possible to get into MySQL, and to delete things, but it's easier
    and cleaner to delete things this way.
    '''

    usage = "usage: %prog -c COURT  (-d | -o) [-t time] [-v VERBOSITY] [-s]"
    parser = OptionParser(usage)
    parser.add_option('-d', '--documents', action='store_true', dest='documents',
        default=False, help="Delete documents")
    parser.add_option('-c', '--court', dest='courtID', metavar="COURTID",
        help="The court to take action upon")
    parser.add_option('-t', '--time', dest='delTime', metavar='delTime',
        help="Take action for all documents newer than this time. Format as follows: YYYY-MM-DD HH:MM:SS" +
        " or YYYY-MM-DD")
    parser.add_option('-v', '--verbosity', dest='verbosity', metavar="VERBOSITY",
        help="Display status messages during execution. Higher values print more verbosity.")
    parser.add_option('-s', '--simulate', action='store_true', dest='simulate',
        default=False, help='Run in simulate mode, printing messages, but not deleting')
    parser.add_option('-o', '--orphans', action='store_true', dest='orphans',
        default=False, help='Delete orphaned citations from the database.')
    parser.add_option('--allcites', action='store_true', dest='cites', default=False,
        help='Delete all citations and their associated documents from the DB')
    (options, args) = parser.parse_args()


    try:
        VERBOSITY = int(options.verbosity)
    except:
        # No verbosity supplied
        VERBOSITY = 0

    SIMULATE = options.simulate
    if SIMULATE:
        print "**********************************************"
        print "* SIMULATION MODE. NO ACTIONS WILL BE TAKEN. *"
        print "**********************************************"
        VERBOSITY = 2

    if options.documents:
        courtID = options.courtID

        delTime = options.delTime
        if delTime is not None:
            try:
                # Parse the date string into a datetime object
                delTime = datetime.datetime(*time.strptime(options.delTime, "%Y-%m-%d %H:%M:%S")[0:6])
            except ValueError:
                try:
                    delTime = datetime.datetime(*time.strptime(options.delTime, "%Y-%m-%d")[0:5])
                except ValueError:
                    parser.error("Unable to parse time. Please use format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")

        # All options are go. Proceed!
        if courtID == 'all':
            # All courts shall be done!
            courts = Court.objects.filter(in_use=True).values_list('courtUUID', flat=True)
            for courtID in courts:
                delete_data_by_time_and_court(courtID, SIMULATE, delTime, VERBOSITY)
                gc.collect()
        else:
            # Just one court, please.
            delete_data_by_time_and_court(courtID, SIMULATE, delTime, VERBOSITY)

    elif options.orphans:
        # We delete orphaned citations
        delete_orphaned_citations(SIMULATE, VERBOSITY)

    elif options.cites:
        # We delete all citations
        delete_all_citations(SIMULATE, VERBOSITY)


    return 0


if __name__ == '__main__':
    main()
