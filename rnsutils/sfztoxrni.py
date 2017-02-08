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

import os
import re
from copy import deepcopy

from rnsutils.instrument import RenoiseInstrument, second_to_renoise_time, db_to_renoise_volume
from rnsutils.utils import ENCODING_NONE, ENCODING_FLAC, ENCODING_OGG, encode_audio_file

__date__ = '2016-01-28'
__updated__ = '2017-02-08'
__author__ = 'olivier@pcedev.com'


def search_case_insensitive_path(path):
    if os.path.exists(path) or path == '':
        return path

    head, tail = os.path.split(path)

    existing_head = search_case_insensitive_path(head)
    if existing_head is None:
        return None
    if existing_head == '':
        existing_head = '.'

    tail = tail.lower()
    for sub in os.listdir(existing_head):
        if sub.lower() == tail:
            return os.path.join(existing_head, sub)

    return None


SFZ_NOTE_LETTER_OFFSET = {'a': 9, 'b': 11, 'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7}


def sfz_note_to_midi_key(sfz_note):
    try:
        return int(sfz_note)
    except ValueError:
        sharp = '#' in sfz_note
        letter = sfz_note[0].lower()
        octave = int(sfz_note[-1])
        return SFZ_NOTE_LETTER_OFFSET[letter] + ((octave + 1) * 12) + (1 if sharp else 0)


class SfzToXrni(object):
    def __init__(self, sfz_path, show_unused=False, encoding=ENCODING_NONE, **kwargs):
        self.encoding = encoding
        self.sfz_path = sfz_path
        self.show_unused = show_unused
        self.sfz_default_path = ''

    def load_default_sample_settings(self, renoise_global_sample, renoise_global_modulation_set):
        renoise_global_modulation_set.Devices.SampleMixerModulationDevice.Cutoff.Value = self.freq_to_cutoff(20000)
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Attack.Value = 0
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Hold.Value = 0
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Decay.Value = 0
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Sustain.Value = 1
        renoise_global_modulation_set.Devices.SampleAhdsrModulationDevice.Release.Value = 0
        renoise_global_modulation_set.FilterType = RenoiseInstrument.FILTER_NONE

        renoise_global_sample.LoopRelease = True
        renoise_global_sample.LoopMode = "Off"
        renoise_global_sample.LoopStart = None
        renoise_global_sample.LoopEnd = None

        renoise_global_sample.Panning = 0.5
        renoise_global_sample.Transpose = 0
        renoise_global_sample.Finetune = 0

        renoise_global_sample.Mapping.BaseNote = 60
        renoise_global_sample.Mapping.NoteStart, renoise_global_sample.Mapping.NoteEnd = (0, 119)
        renoise_global_sample.Mapping.VelocityStart, renoise_global_sample.Mapping.VelocityEnd = (0, 127)

    def convert_instrument(self, sfz_filename, renoise_instrument):

        renoise_instrument.root.find('GlobalProperties/*[Name="SF2 reverb"]').Value = 0
        renoise_instrument.root.find('GlobalProperties/*[Name="SF2 chorus"]').Value = 0
        renoise_instrument.root.SampleGenerator.KeyzoneOverlappingMode = RenoiseInstrument.OVERLAP_ALL

        renoise_instrument.comment = "Converted from SFZ {} with sfztoxrni " \
                                     "( https://gitlab.com/zeograd/rnsutils )".format(sfz_filename)

        renoise_instrument.root.GlobalProperties.MacrosVisible = False

        with open(sfz_filename, 'rt') as sfz_file:
            # convert instrument meta data
            renoise_instrument.name = os.path.basename(sfz_filename)

            # load global properties if any
            renoise_default_sample = deepcopy(renoise_instrument.sample_template)
            renoise_default_modulation_set = deepcopy(renoise_instrument.modulation_set_template)

            self.load_default_sample_settings(renoise_default_sample, renoise_default_modulation_set)

            sfz_content = self.parse_sfz(sfz_file.readlines())

            section_idx = 0

            for section_name, section_content in sfz_content:

                if section_name in ('group', 'global'):
                    self.convert_section(section_name, section_content, renoise_default_sample,
                                         renoise_default_modulation_set, renoise_default_sample,
                                         renoise_default_modulation_set, renoise_instrument)
                    continue

                # convert sample meta data in xml
                renoise_sample = deepcopy(renoise_default_sample)
                renoise_modulation_set = deepcopy(renoise_default_modulation_set)

                # force modulation set index to 0, but the sf2 modulation set remains easily enabled if needed by user
                renoise_sample.ModulationSetIndex = 0

                renoise_sample.FileName = None

                self.convert_section(section_name, section_content, renoise_sample, renoise_modulation_set,
                                     renoise_default_sample, renoise_default_modulation_set, renoise_instrument)

                if renoise_sample.FileName:
                    renoise_instrument.root.SampleGenerator.Samples.append(renoise_sample)
                    renoise_instrument.root.SampleGenerator.ModulationSets.append(renoise_modulation_set)

                    # copy wav content from sfz to renoise
                    sample_filename = search_case_insensitive_path(
                        os.path.join(self.sfz_path, self.sfz_default_path, str(renoise_sample.FileName)))

                    if sample_filename is None:
                        logging.info("missing sample file '%s'", renoise_sample.FileName)
                    else:
                        with open(sample_filename, 'rb') as sample_content:
                            renoise_instrument.sample_data.append(encode_audio_file(sample_content.read(), self.encoding))

                section_idx += 1

    def parse_sfz(self, sfz):

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

    def convert_section(self, section_name, section_content, renoise_sample, renoise_modulation_set,
                        renoise_default_sample, renoise_default_modulation_set, renoise_instrument):

        unused_keys = []

        for key in section_content.keys():
            value = section_content[key].lower()
            if key == 'sample':
                renoise_sample.FileName = re.sub(r'\\+', r'/', value)

                # remove first char if file separator
                if renoise_sample.FileName.pyval[0] in (r'/', r'\\'):
                    renoise_sample.FileName = renoise_sample.FileName.pyval[1:]

                renoise_sample.Name, _ = os.path.splitext(os.path.basename(renoise_sample.FileName.pyval))
            elif key == 'lokey':
                renoise_sample.Mapping.NoteStart = sfz_note_to_midi_key(value)
            elif key == 'hikey':
                renoise_sample.Mapping.NoteEnd = sfz_note_to_midi_key(value)
            elif key == 'lovel':
                renoise_sample.Mapping.VelocityStart = value
            elif key == 'hivel':
                renoise_sample.Mapping.VelocityEnd = value
            elif key == 'pitch_keycenter':
                renoise_sample.Mapping.BaseNote = sfz_note_to_midi_key(value)
            elif key == 'ampeg_attack':
                renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Attack.Value = second_to_renoise_time(
                    float(value))
            elif key == 'ampeg_hold':
                renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Hold.Value = second_to_renoise_time(
                    float(value))
            elif key == 'ampeg_decay':
                renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Decay.Value = second_to_renoise_time(
                    float(value))
            elif key == 'ampeg_sustain':
                renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Sustain.Value = 1 - float(value) / 100.
            elif key == 'ampeg_release':
                renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Release.Value = second_to_renoise_time(
                    float(value))
            elif key == 'tune':
                renoise_sample.Finetune = int(128 * float(value) / 100.)
            elif key == 'transpose':
                renoise_sample.Transpose = value
            elif key == 'volume':
                renoise_sample.Volume = db_to_renoise_volume(float(value))
            elif key == 'pan':
                renoise_sample.Panning = 0.5 + float(value) / 200.
            elif key == 'fil_type':
                if value.lower().startswith('lp'):
                    renoise_modulation_set.FilterType = RenoiseInstrument.FILTER_CLEAN_LP
                elif value.lower().startswith('hp'):
                    renoise_modulation_set.FilterType = RenoiseInstrument.FILTER_CLEAN_HP
                else:
                    renoise_modulation_set.FilterType = RenoiseInstrument.FILTER_NONE
            elif key == 'loop_mode':
                if value == 'one_shot':
                    renoise_sample.LoopMode = RenoiseInstrument.LOOP_FORWARD
                else:
                    renoise_sample.LoopMode = RenoiseInstrument.LOOP_NONE
            elif key == 'loop_start':
                renoise_sample.LoopStart = value
            elif key == 'loop_end':
                renoise_sample.LoopEnd = value
            elif key == 'seq_position':
                if int(value) > 1:
                    logging.info("Switch the entire instrument to sample cycling")
                    renoise_instrument.root.SampleGenerator.KeyzoneOverlappingMode = RenoiseInstrument.OVERLAP_CYCLE
            elif key == 'seq_length':
                pass
            elif key == 'lorand':
                if float(value) > 0:
                    logging.info("Switch the entire instrument to random sample round robin")
                    renoise_instrument.root.SampleGenerator.KeyzoneOverlappingMode = RenoiseInstrument.OVERLAP_RANDOM
            elif key == 'hirand':
                if float(value) < 1:
                    logging.info("Switch the entire instrument to random sample round robin")
                    renoise_instrument.root.SampleGenerator.KeyzoneOverlappingMode = RenoiseInstrument.OVERLAP_RANDOM
            elif key == 'group':
                logging.info("Ignoring mute group info")
            elif key == 'off_by':
                logging.info("Ignoring mute group info")
            elif key == 'default_path':
                self.sfz_default_path = re.sub(r'\\+', r'/', value)

                # remove first char if file separator
                if self.sfz_default_path[0] in (r'/', r'\\'):
                    self.sfz_default_path = self.sfz_default_path[1:]

            else:
                unused_keys.append(key)

        # disable loop when no loop duration was set
        if renoise_sample.LoopStart.pyval is None or renoise_sample.LoopEnd.pyval is None:
            renoise_sample.LoopMode = RenoiseInstrument.LOOP_NONE

        if unused_keys and self.show_unused:
            sys.stderr.write(
                "Unused key(s) for section {}:\n{}\n".format(section_name,
                                                             "\n".join([" - " + k for k in unused_keys])))


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.9"
    program_build_date = "%s" % __updated__

    program_version_string = 'sfztoxrni %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Convert SFZ file into renoise instrument'''
    program_license = "GPL v3+ 2016-2017 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-e", "--encode", dest="encoding", choices=[ENCODING_NONE, ENCODING_FLAC, ENCODING_OGG],
                            default=ENCODING_FLAC, help="encode samples into given format [default: %(default)s]")
        parser.add_argument("-f", "--force", dest="force", default=False, action="store_true",
                            help="force overwriting existing files [default: %(default)s]")
        parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False,
                            help="quiet operation [default: %(default)s]")
        parser.add_argument("-o", "--ouput-dir", dest="output_dir",
                            help="output directory [default: current directory]")
        parser.add_argument("-t", dest="template", help="template filename [default: %(default)s]",
                            default="empty-31.xrni")
        parser.add_argument("-u", "--unused", dest="show_unused", action="store_true", default=True,
                            help="show unused generators [default: %(default)s]")
        parser.add_argument("--no-unused", dest="show_unused", action="store_false")
        parser.add_argument("-v", "--version", action="version", version=program_version_string)

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
            sfz_path = os.path.dirname(sfz_filename)
            sfz_to_xrni = SfzToXrni(sfz_path=sfz_path, **vars(opts))

            renoise_instrument = RenoiseInstrument(template_filename=opts.template)
            sfz_to_xrni.convert_instrument(sfz_filename, renoise_instrument)

            filename_without_extension, extension = os.path.splitext(os.path.basename(sfz_filename))
            output_filename = os.path.join(opts.output_dir or sfz_path, '{}.xrni'.format(filename_without_extension))
            renoise_instrument.save(output_filename, overwrite=opts.force)

            if not opts.quiet:
                print("Saved {}".format(output_filename))
        except Exception:
            if not opts.quiet:
                print("FAILED")
            logging.exception("Failed to convert instrument")

    return 0


if __name__ == "__main__":
    sys.exit(main())
