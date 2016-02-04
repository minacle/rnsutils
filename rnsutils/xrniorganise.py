# xrniorganise. Organise your XRNI files
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


def clean_filename(value):
    import re
    value = re.sub(r'[\./\\]', '_', value)
    value = re.sub('[^\w\s\-]', '', value).strip().lower()
    return value


def get_destination_directories(tags, opts):
    if tags is None:
        return [os.path.join(opts.output_dir, "untagged")]

    return [os.path.join(opts.output_dir, clean_filename(str(tag))) for tag in tags]


def clean_directory(output_dir):
    """clean directory of all symlinks and subdirs. Aborts if any regular file is present"""
    for file in os.listdir(output_dir):
        file = os.path.join(output_dir, file)
        if os.path.islink(file):
            os.unlink(file)
        elif os.path.isdir(file):
            clean_directory(file)
            os.rmdir(file)
        else:
            raise FileExistsError("Non symlink found while cleaning : {}".format(file))


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.8"
    program_build_date = "%s" % __updated__

    program_version_string = 'xrniorganise %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Organise XRNI according to their tags'''
    program_license = "GPL v3+ 2016 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-c", "--clean", dest="clean", action="store_true", default=False,
                            help="clean destination directory before operations")
        parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true", default=False,
                            help="don't actually perform filesystem operations [default: %(default)s]")
        parser.add_argument("-r", "--recursive", dest="recurse_dir", action="store_true", default=False,
                            help="recursively parse directories [default: %(default)s]")
        parser.add_argument("-o", "--ouput-dir", dest="output_dir", help="output directory", required=True)
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

    if opts.clean:
        if opts.dry_run:
            print("I would clean {}".format(opts.output_dir))
        else:
            clean_directory(opts.output_dir)

    for xrni_filename in opts.xrni_filename:
        organise_file(opts, xrni_filename)

    return 0


def organise_file(opts, filename):
    full_filename = os.path.realpath(filename)

    # recursively parse directory if told to
    if os.path.isdir(full_filename):
        if opts.recurse_dir:
            for file in os.listdir(full_filename):
                organise_file(opts, os.path.join(full_filename, file))
        return

    renoise_instrument = RenoiseInstrument(full_filename)
    tags = renoise_instrument.tags
    destination_directories = get_destination_directories(tags, opts)
    if opts.dry_run:
        for directory in destination_directories:
            print("I would link {} to {}".format(full_filename,
                                                 os.path.join(directory, os.path.basename(filename))))
    else:
        for directory in destination_directories:

            try:
                os.makedirs(directory)
            except FileExistsError:
                pass

            link_full_filename = os.path.join(directory, os.path.basename(filename))

            if os.path.islink(link_full_filename):
                os.unlink(link_full_filename)

            os.symlink(full_filename, link_full_filename)


if __name__ == "__main__":
    sys.exit(main())
