# sfztoxrni. convert SFZ file to renoise instrument
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
import math
import sys

import io
import os
from copy import deepcopy

from rnsutils.instrument import RenoiseInstrument

__date__ = '2016-01-28'
__updated__ = '2016-01-28'
__author__ = 'olivier@pcedev.com'


class SfzToXrni(object):
    def __init__(self, show_unused=False, **kwargs):
        self.show_unused = show_unused
        self.unused_gens = set()

    def convert_bag(self, sf2_bag, renoise_sample, renoise_modulation_set, default_sample, default_modulation_set):

        # sample looping
        renoise_sample.LoopRelease = sf2_bag.sample_loop_on_noteoff
        renoise_sample.LoopMode = "Forward" if sf2_bag.sample_loop else "Off"
        renoise_sample.LoopStart = sf2_bag.cooked_loop_start
        renoise_sample.LoopEnd = sf2_bag.cooked_loop_end

        # sample panning
        renoise_sample.Panning = (sf2_bag.pan and sf2_bag.pan + 0.5) or default_sample.Panning

        # sample tuning
        renoise_sample.Transpose = sf2_bag.tuning or default_sample.Transpose
        renoise_sample.FineTune = (sf2_bag.fine_tuning and (int(128 * sf2_bag.fine_tuning) / 100.)) or (
            sf2_bag.sample and int(128 * (sf2_bag.sample.pitch_correction) / 100.)) or default_sample.FineTune

        # volume envelope
        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Attack.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_attack) or default_modulation_set.ahdsr_attack

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Decay.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_decay) or default_modulation_set.ahdsr_decay

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Hold.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_hold) or default_modulation_set.ahdsr_hold

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Sustain.Value = (
                                                                                       sf2_bag.volume_envelope_sustain is not None and (
                                                                                           max(0,
                                                                                               1 - sf2_bag.volume_envelope_sustain / 96.))) or default_modulation_set.ahdsr_sustain

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Release.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_release) or default_modulation_set.ahdsr_release

        # low pass filter
        renoise_modulation_set.Devices.SampleMixerModulationDevice.Cutoff.Value = self.freq_to_cutoff(
            sf2_bag.lp_cutoff) if sf2_bag.lp_cutoff else default_modulation_set.lp_cutoff

        # base note
        renoise_sample.Mapping.BaseNote = sf2_bag.base_note or (
            sf2_bag.sample and sf2_bag.sample.original_pitch) or default_sample.Mapping.BaseNote

        # key mapping (key range and velocity)
        renoise_sample.Mapping.NoteStart, renoise_sample.Mapping.NoteEnd = sf2_bag.key_range or (
            default_sample.Mapping.NoteStart, default_sample.Mapping.NoteEnd)

        renoise_sample.Mapping.VelocityStart, renoise_sample.Mapping.VelocityEnd = sf2_bag.velocity_range or (
            default_sample.Mapping.VelocityStart, default_sample.Mapping.VelocityEnd)

    def load_global_sample_settings(self, sf2_instrument, renoise_global_sample, renoise_global_modulation_set):
        global_chorus_send = 0
        global_reverb_send = 0

        for sf2_bag_idx, sf2_bag in enumerate(sf2_instrument.bags):
            if sf2_bag.sample is None:
                self.convert_bag(sf2_bag, renoise_global_sample, renoise_global_modulation_set, renoise_global_sample,
                                 renoise_global_modulation_set)
                global_chorus_send = sf2_bag.chorus_send or 0
                global_reverb_send = sf2_bag.reverb_send or 0

                self.check_unused_bags(sf2_bag_idx, sf2_instrument.name, sf2_bag)

        return global_chorus_send, global_reverb_send

    def load_default_sample_settings(self, renoise_global_sample, renoise_global_modulation_set):
        renoise_global_modulation_set.Devices.SampleMixerModulationDevice.Cutoff.Value = self.freq_to_cutoff(20000)
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Attack.Value = 0
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Hold.Value = 0
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Decay.Value = 0
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Sustain.Value = 1
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Release.Value = 0

        renoise_global_sample.Panning = 0.5
        renoise_global_sample.Transpose = 0
        renoise_global_sample.FineTune = 0

        renoise_global_sample.Mapping.BaseNote = 60
        renoise_global_sample.Mapping.NoteStart, renoise_global_sample.Mapping.NoteEnd = (0, 119)
        renoise_global_sample.Mapping.VelocityStart, renoise_global_sample.Mapping.VelocityEnd = (0, 127)

    def convert_instrument(self, sfz_filename, renoise_instrument):
        with open(sfz_filename, 'rt') as sfz_file:
            # convert instrument meta data
            renoise_instrument.name = os.path.basename(sfz_filename)

            # load global properties if any
            renoise_global_sample = deepcopy(renoise_instrument.sample_template)
            renoise_global_modulation_set = deepcopy(renoise_instrument.modulation_set_template)

            self.load_default_sample_settings(renoise_global_sample, renoise_global_modulation_set)

            sfz_content = self.parse_sfz(sfz_file.readlines())

            for section_name, section_content in sfz_content:
                if section_name == 'group':
                    pass
                    # self.convert_section(section_content, renoise_global_sample, renoise_global_modulation_set, renoise_global_sample, renoise_global_modulation_set)

            section_idx = 0

            for section_name, section_content in sfz_content:
                if section_name == 'group':
                    continue

                # convert sample meta data in xml
                renoise_sample = deepcopy(renoise_instrument.sample_template)
                renoise_modulation_set = deepcopy(renoise_instrument.modulation_set_template)

                # link sample to its dedicated modulation set
                renoise_sample.ModulationSetIndex = section_idx
                #                self.convert_bag(sf2_bag, renoise_sample, renoise_modulation_set, renoise_global_sample,
                #                                 renoise_global_modulation_set)

                #                renoise_sample.Name = sf2_bag.sample.name

                renoise_instrument.root.SampleGenerator.Samples.append(renoise_sample)
                renoise_instrument.root.SampleGenerator.ModulationSets.append(renoise_modulation_set)

                # copy wav content from sf2 to renoise
                wav_content = io.BytesIO()
                #                sf2_bag.sample.export(wav_content)
                renoise_instrument.sample_data.append(wav_content.getvalue())

                section_idx += 1

    def parse_sfz(self, sfz):

        import re
        match_section = re.compile('^<(.*)>$')

        sections = []
        partial_section = {}
        current_section = None

        for line in sfz:
            line = line.strip()
            matching = match_section.match(line)
            if matching:
                if partial_section:
                    sections.append((current_section, partial_section))
                    partial_section = {}
                current_section = matching.group(1)
            elif "=" in line:
                key, _, value = line.partition('=')
                partial_section[key] = value

        if partial_section:
            sections.append((current_section, partial_section))
            partial_section = {}

        return sections

    def freq_to_cutoff(self, param):
        return 127. * max(0, min(1, math.log(param / 130.) / 5)) if param else None

    def to_renoise_time(self, envelope_attenuation):
        return math.pow(envelope_attenuation / 60., 1 / 3.) if envelope_attenuation else None


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.6"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Convert SFZ file into renoise instrument'''
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
                            help="quiet operation [default: %(default)s]")
        parser.add_argument("-o", "--ouput-dir", dest="output_dir",
                            help="output directory [default: current directory]")
        parser.add_argument("-t", dest="template", help="template filename [default: %(default)s]",
                            default="empty-31.xrni")

        parser.add_argument("sfz_filename", help="input file in SFZ format", nargs="+")

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

    for sfz_filename in opts.sfz_filename:

        if not opts.quiet:
            print("Reading instrument from '{}'".format(sfz_filename))

        # noinspection PyBroadException
        try:
            sfz_to_xrni = SfzToXrni(**vars(opts))

            renoise_instrument = RenoiseInstrument(template_filename=opts.template)
            sfz_to_xrni.convert_instrument(sfz_filename, renoise_instrument)

            output_filename = os.path.join(opts.output_dir or '', '{}.xrni'.format(renoise_instrument.name))
            renoise_instrument.save(output_filename)

            if not opts.quiet:
                print(" saved {}".format(output_filename))
        except Exception:
            if not opts.quiet:
                print(" FAILED")
            logging.exception("Failed to convert instrument")

    return 0


if __name__ == "__main__":
    sys.exit(main())
