# xrnireencode. reencode samples in XRNI files
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
from rnsutils.utils import ENCODING_FLAC, ENCODING_OGG, encode_audio_file

__date__ = '2016-01-31'
__updated__ = '2016-01-31'
__author__ = 'olivier@pcedev.com'


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.6"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Reencode samples in renoise instrument'''
    program_license = "GPL v3+ 2016 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-e", "--encode", dest="encoding", choices=[ENCODING_FLAC, ENCODING_OGG],
                            default=ENCODING_FLAC, help="encode samples into given format [default: %(default)s]")
        parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False,
                            help="quiet operation [default: %(default)s]")
        parser.add_argument("-o", "--ouput-dir", dest="output_dir",
                            help="output directory [default: current directory]")

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

        if not opts.quiet:
            print("Reencoding samples from '{}'".format(xrni_filename))

        # noinspection PyBroadException
        try:
            renoise_instrument = RenoiseInstrument(xrni_filename)

            # reencode all samples
            renoise_instrument.sample_data = [encode_audio_file(sample, opts.encoding) for sample in
                                              renoise_instrument.sample_data]

            # save the output file
            filename_without_extension, extension = os.path.splitext(os.path.basename(xrni_filename))
            output_filename = os.path.join(opts.output_dir or os.path.dirname(xrni_filename),
                                           '{}.{}.xrni'.format(filename_without_extension, opts.encoding))
            renoise_instrument.save(output_filename)

            if not opts.quiet:
                print("Saved {}".format(output_filename))
        except Exception:
            if not opts.quiet:
                print("FAILED")
            logging.exception("Failed to reencode instrument")

    return 0


if __name__ == "__main__":
    sys.exit(main())
