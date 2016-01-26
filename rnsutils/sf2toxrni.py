# sf2toxrni. convert sound font 2 file to renoise instrument
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
import io
import logging
import math
import os
import sys
from copy import deepcopy

from sf2utils.generator import Sf2Gen
from sf2utils.sf2parse import Sf2File

from rnsutils.instrument import RenoiseInstrument

__date__ = '2016-01-22'
__updated__ = '2016-01-25'
__author__ = 'olivier@pcedev.com'


class Sf2ToXrni(object):
    WHITELIST_UNUSED_GEN_OPERS = {Sf2Gen.OPER_INITIAL_ATTENUATION}

    def __init__(self, show_unused=False, **kwargs):
        self.show_unused = show_unused
        self.unused_gens = set()

    def convert_bag(self, sf2_bag, renoise_sample, renoise_modulation_set, default_sample, default_modulation_set):
        renoise_sample.LoopRelease = sf2_bag.sample_loop_on_noteoff
        renoise_sample.LoopMode = "Forward" if sf2_bag.sample_loop else "Off"
        renoise_sample.LoopStart = sf2_bag.cooked_loop_start
        renoise_sample.LoopEnd = sf2_bag.cooked_loop_end
        renoise_sample.Panning = (sf2_bag.pan or 0) + 0.5
        renoise_sample.Transpose = sf2_bag.tuning or 0
        renoise_sample.FineTune = int(128 * (sf2_bag.fine_tuning or 0) / 100.)

        renoise_modulation_set.adhsr_release = self.to_attenuation(
            sf2_bag.volume_envelope_release) if sf2_bag.volume_envelope_release \
            else default_modulation_set.adhsr_release

        renoise_modulation_set.lp_cutoff = self.freq_to_cutoff(
            sf2_bag.lp_cutoff) if sf2_bag.lp_cutoff else default_modulation_set.lp_cutoff

        renoise_sample.Mapping.BaseNote = sf2_bag.base_note or 60
        renoise_sample.Mapping.NoteStart, renoise_sample.Mapping.NoteEnd = sf2_bag.key_range or (0, 119)
        renoise_sample.Mapping.VelocityStart, renoise_sample.Mapping.VelocityEnd = sf2_bag.velocity_range or (0, 127)

    def load_global_sample_settings(self, sf2_instrument, renoise_global_sample, renoise_global_modulation_set):
        global_chorus_send = 0
        global_reverb_send = 0

        for sf2_bag in sf2_instrument.bags:
            if sf2_bag.sample is None:
                self.convert_bag(sf2_bag, renoise_global_sample, renoise_global_modulation_set, renoise_global_sample,
                                 renoise_global_modulation_set)
                global_chorus_send = sf2_bag.chorus_send or 0
                global_reverb_send = sf2_bag.reverb_send or 0

        return global_chorus_send, global_reverb_send

    def load_default_sample_settings(self, renoise_global_sample, renoise_global_modulation_set):
        renoise_global_modulation_set.lp_cutoff = self.freq_to_cutoff(20000)
        renoise_global_modulation_set.ahdsr_release = 0

    def convert_instrument(self, sf2_instrument, renoise_instrument):
        # convert instrument meta data
        renoise_instrument.name = sf2_instrument.name

        # load global properties if any
        renoise_global_sample = deepcopy(renoise_instrument.sample_template)
        renoise_global_modulation_set = deepcopy(renoise_instrument.modulation_set_template)

        self.load_default_sample_settings(renoise_global_sample, renoise_global_modulation_set)
        global_chorus_send, global_reverb_send = self.load_global_sample_settings(sf2_instrument, renoise_global_sample,
                                                                                  renoise_global_modulation_set)

        chorus_send = []
        reverb_send = []

        bag_idx = 0

        for sf2_bag in sf2_instrument.bags:

            # skip global zone
            if sf2_bag.sample is None:
                continue

            # convert sample meta data in xml
            renoise_sample = deepcopy(renoise_instrument.sample_template)
            renoise_modulation_set = deepcopy(renoise_instrument.modulation_set_template)

            # link sample to its dedicated modulation set
            renoise_sample.ModulationSetIndex = bag_idx
            self.convert_bag(sf2_bag, renoise_sample, renoise_modulation_set, renoise_global_sample,
                             renoise_global_modulation_set)

            renoise_sample.Name = sf2_bag.sample.name

            renoise_instrument.root.SampleGenerator.Samples.append(renoise_sample)
            renoise_instrument.root.SampleGenerator.ModulationSets.append(renoise_modulation_set)

            # keep track of chorus
            sample_chorus_send = sf2_bag.chorus_send
            if sample_chorus_send:
                chorus_send.append(sample_chorus_send)

            # keep track of reverb
            sample_reverb_send = sf2_bag.reverb_send
            if sample_reverb_send:
                reverb_send.append(sample_reverb_send)

            # copy wav content from sf2 to renoise
            wav_content = io.BytesIO()
            sf2_bag.sample.export(wav_content)
            renoise_instrument.sample_data.append(wav_content.getvalue())

            # check which generator where not used from the sf2, excluding those which have no mapping or are
            # ignored on purpose
            current_instrument_unused_gens = {gen for gen in sf2_bag.unused_gens if
                                              gen.oper not in self.WHITELIST_UNUSED_GEN_OPERS}
            self.unused_gens |= current_instrument_unused_gens

            if current_instrument_unused_gens and self.show_unused:
                sys.stderr.write("Unused generator(s) for instrument {}, bag #{}:\n{}\n".format(
                    renoise_instrument.name, bag_idx,
                    "\n".join([gen.pretty_print() for gen in current_instrument_unused_gens])))

            bag_idx += 1

        # use average reverb send
        try:
            renoise_instrument.root.find('GlobalProperties/*[Name="SF2 reverb"]').Value = (0 if len(
                reverb_send) == 0 else sum(reverb_send) / float(len(reverb_send))) + global_reverb_send
        except AttributeError:
            pass

        # usa average chorus send
        try:
            renoise_instrument.root.find('GlobalProperties/*[Name="SF2 chorus"]').Value = (0 if len(
                chorus_send) == 0 else sum(chorus_send) / float(len(chorus_send))) + global_chorus_send
        except AttributeError:
            pass

    def freq_to_cutoff(self, param):
        return 127. * max(0, min(1, math.log(param / 130.) / 5))

    def to_attenuation(self, envelope_attenuation):
        return math.pow((envelope_attenuation or 0) / 60., 1 / 3.)


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.5"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Convert sf2 file into renoise instrument'''
    program_license = "GPL v3+ 2016 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False,
                            help="quiet operation [default: %(default)s")
        parser.add_argument("-u", "--unused", dest="show_unused", action="store_true", default=True)
        parser.add_argument("--no-unused", dest="show_unused", action="store_false")
        parser.add_argument("-o", "--ouput-dir", dest="output_dir",
                            help="output directory [default: current directory]")

        parser.add_argument("sf2_filename", help="input file in SoundFont2 format")

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

    with open(opts.sf2_filename, "rb") as sf2_file:
        sf2 = Sf2File(sf2_file)

        # print(sf2.pretty_print())

        sf2_to_xrni = Sf2ToXrni(**vars(opts))

        for instrument_idx, sf2_instrument in enumerate(sf2.instruments):
            if sf2_instrument.is_sentinel():
                continue

            if not opts.quiet:
                print("Converting '{}'...".format(sf2_instrument.name), end='')

            # noinspection PyBroadException
            try:
                renoise_instrument = RenoiseInstrument()
                sf2_to_xrni.convert_instrument(sf2_instrument, renoise_instrument)

                output_filename = os.path.join(opts.output_dir or '',
                                               '{}_{}.xrni'.format(instrument_idx, renoise_instrument.name))
                # noinspection PyTypeChecker
                renoise_instrument.save(output_filename)
                if not opts.quiet:
                    print(" saved {}".format(output_filename))
            except Exception:
                if not opts.quiet:
                    print(" FAILED")
                logging.exception("Failed to convert instrument")

                # pprint.pprint(sf2.samples)
                # sf2.samples[3].export('/tmp/test.wav')

                # pprint.pprint(sf2.presets)
                # pprint.pprint(sf2.instruments)
                #
                # for instrument in sf2.instruments:
                #     print(instrument.pretty_print())

    return 0


if __name__ == "__main__":
    sys.exit(main())
