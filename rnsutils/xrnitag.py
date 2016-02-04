# xrnitag. manipulate XRNI tags
# Copyright (C) 2016  Olivier Jolly
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import argparse
import logging
import sys

import os

from rnsutils.instrument import RenoiseInstrument

__date__ = '2016-02-02'
__updated__ = '2016-02-02'
__author__ = 'olivier@pcedev.com'

ACTION_VIEW = 0
ACTION_EDIT = 1
ACTION_DELETE = 2
ACTION_APPEND = 3
ACTION_CLEAR = 4


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.8"
    program_build_date = "%s" % __updated__

    program_version_string = 'xrnitag %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Display or change XRNI tags'''
    program_license = "GPL v3+ 2016 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-a", "--add", dest="tags_to_add", action="append", help="add a tag")
        parser.add_argument("-c", "--clear", dest="action", action="store_const", const=ACTION_CLEAR,
                            default=ACTION_VIEW, help="clear all tags")
        parser.add_argument("-r", "--remove", dest="tags_to_remove", action="append", help="remove a tag")
        parser.add_argument("-v", "--version", action="version", version=program_version_string)

        parser.add_argument("xrni_filename", help="input file in XRNI format", nargs="+")

        # process options
        opts = parser.parse_args(argv)

    except Exception as e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

    if opts.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    for xrni_filename in opts.xrni_filename:
        renoise_instrument = RenoiseInstrument(xrni_filename)

        if opts.action == ACTION_CLEAR:
            del renoise_instrument.tags
            renoise_instrument.save(xrni_filename, overwrite=True)

        if opts.tags_to_add or opts.tags_to_remove:
            for tag in opts.tags_to_remove or []:
                renoise_instrument.remove_tag(tag)
            for tag in opts.tags_to_add or []:
                renoise_instrument.append_tag(tag)
            renoise_instrument.save(xrni_filename, overwrite=True)
        else:
            tags = renoise_instrument.tags
            if tags:
                print("\n".join([str(tag) for tag in tags]))
            else:
                print("<no tag found>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
