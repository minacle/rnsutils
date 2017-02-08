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
import logging
import math
import sys

import io
import os
from copy import deepcopy

from rnsutils.instrument import RenoiseInstrument
from rnsutils.utils import ENCODING_NONE, encode_audio_file, ENCODING_FLAC, ENCODING_OGG, expand_keymap
from sf2utils.generator import Sf2Gen
from sf2utils.sf2parse import Sf2File

__date__ = '2016-01-22'
__updated__ = '2017-02-08'
__author__ = 'olivier@pcedev.com'


class Sf2ToXrni(object):
    WHITELIST_UNUSED_GEN_OPERS = {Sf2Gen.OPER_INITIAL_ATTENUATION, Sf2Gen.OPER_VIB_LFO_TO_PITCH,
                                  Sf2Gen.OPER_DELAY_VIB_LFO, Sf2Gen.OPER_FREQ_VIB_LFO}

    def __init__(self, show_unused=False, encoding=ENCODING_NONE, force_center=False, **kwargs):
        self.show_unused = show_unused
        self.encoding = encoding
        self.unused_gens = set()
        self.force_center = force_center

    def convert_bag(self, sf2_bag, renoise_sample, renoise_modulation_set, default_sample, default_modulation_set):

        # sample looping
        renoise_sample.LoopRelease = sf2_bag.sample_loop_on_noteoff
        renoise_sample.LoopMode = "Forward" if sf2_bag.sample_loop else "Off"
        renoise_sample.LoopStart = sf2_bag.cooked_loop_start
        renoise_sample.LoopEnd = sf2_bag.cooked_loop_end

        # sample panning
        renoise_sample.Panning = (sf2_bag.pan and sf2_bag.pan + 0.5) or default_sample.Panning
        if self.force_center:
            renoise_sample.Panning = 0.5

        # sample tuning
        renoise_sample.Transpose = sf2_bag.tuning or default_sample.Transpose
        renoise_sample.Finetune = (sf2_bag.fine_tuning and (int(128 * sf2_bag.fine_tuning) / 100.)) or (
            sf2_bag.sample and int(128 * (sf2_bag.sample.pitch_correction) / 100.)) or default_sample.Finetune

        # volume envelope
        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Attack.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_attack) or default_modulation_set.ahdsr_attack

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Decay.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_decay) or default_modulation_set.ahdsr_decay

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Hold.Value = self.to_renoise_time(
            sf2_bag.volume_envelope_hold) or default_modulation_set.ahdsr_hold

        renoise_modulation_set.Devices.SampleAhdsrModulationDevice.Sustain.Value = \
            (sf2_bag.volume_envelope_sustain is not None and (
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

        # key mapping (key range, velocity and key mapping to pitch)
        renoise_sample.Mapping.NoteStart, renoise_sample.Mapping.NoteEnd = sf2_bag.key_range or (
            default_sample.Mapping.NoteStart, default_sample.Mapping.NoteEnd)

        renoise_sample.Mapping.VelocityStart, renoise_sample.Mapping.VelocityEnd = sf2_bag.velocity_range or (
            default_sample.Mapping.VelocityStart, default_sample.Mapping.VelocityEnd)

        midi_key_pitch_influence = sf2_bag.midi_key_pitch_influence
        if midi_key_pitch_influence != 0 and midi_key_pitch_influence != 100 and midi_key_pitch_influence is not None:
            sys.stderr.write(
                "Unsupported MIDI key influence on pitch, assuming 100%: {}%\n".format(midi_key_pitch_influence))

        renoise_sample.Mapping.MapKeyToPitch = (midi_key_pitch_influence != 0)

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
        renoise_global_sample.Finetune = 0

        renoise_global_sample.Mapping.BaseNote = 60
        renoise_global_sample.Mapping.NoteStart, renoise_global_sample.Mapping.NoteEnd = (0, 119)
        renoise_global_sample.Mapping.VelocityStart, renoise_global_sample.Mapping.VelocityEnd = (0, 127)

    def convert_instrument(self, sf2_instrument, renoise_instrument):
        # convert instrument meta data
        renoise_instrument.name = sf2_instrument.name

        renoise_instrument.comment = "Converted from instrument {} with sf2toxrni " \
                                     "( https://gitlab.com/zeograd/rnsutils )" \
                                     "\n---\n{}".format(sf2_instrument.name, sf2_instrument.parent.info)

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
            renoise_instrument.sample_data.append(encode_audio_file(wav_content.getvalue(), self.encoding))

            # check which generator where not used from the sf2, excluding those which have no mapping or are
            # ignored on purpose
            self.check_unused_bags(bag_idx, renoise_instrument.name, sf2_bag)

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

    def check_unused_bags(self, bag_idx, instrument_name, sf2_bag):
        current_instrument_unused_gens = {gen for gen in sf2_bag.unused_gens if
                                          gen.oper not in self.WHITELIST_UNUSED_GEN_OPERS}
        self.unused_gens |= current_instrument_unused_gens
        if current_instrument_unused_gens and self.show_unused:
            sys.stderr.write("Unused generator(s) for instrument {}, bag #{}:\n{}\n".format(
                instrument_name, bag_idx,
                "\n".join([gen.pretty_print() for gen in current_instrument_unused_gens])))

    def freq_to_cutoff(self, param):
        return 127. * max(0, min(1, math.log(param / 130.) / 5))

    def to_renoise_time(self, envelope_attenuation):
        return math.pow(envelope_attenuation / 60., 1 / 3.) if envelope_attenuation else None


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.9"
    program_build_date = "%s" % __updated__

    program_version_string = 'sf2toxrni %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Convert sf2 file into renoise instrument'''
    program_license = "GPL v3+ 2016-2017 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-c", "--force-center", dest="force_center", action="store_true", default="False",
                            help="force panning of generated samples to center [default: %(default)s]")
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-e", "--encode", dest="encoding", choices=[ENCODING_NONE, ENCODING_FLAC, ENCODING_OGG],
                            default=ENCODING_FLAC, help="encode samples into given format [default: %(default)s]")
        parser.add_argument("-f", "--force", dest="force", default=False, action="store_true",
                            help="force overwriting existing files [default: %(default)s]")
        parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False,
                            help="quiet operation [default: %(default)s]")
        parser.add_argument("-i", "--instrument", dest="instruments_index", action="append", type=int,
                            help="instrument index to extract [default: all]")
        parser.add_argument("--no-expand-keymap", dest="no_expand_keymap", action="store_true")
        parser.add_argument("-o", "--ouput-dir", dest="output_dir",
                            help="output directory [default: current directory]")
        parser.add_argument("-t", dest="template", help="template filename [default: %(default)s]",
                            default="empty-31.xrni")
        parser.add_argument("-u", "--unused", dest="show_unused", action="store_true", default=True,
                            help="show unused generators [default: %(default)s]")
        parser.add_argument("--no-unused", dest="show_unused", action="store_false")
        parser.add_argument("-v", "--version", action="version", version=program_version_string)

        parser.add_argument("sf2_filename", help="input file in SoundFont2 format", nargs="+")

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

    for sf2_filename in opts.sf2_filename:

        if not opts.quiet:
            print("Reading instruments from '{}'".format(sf2_filename))

        with open(sf2_filename, "rb") as sf2_file:
            sf2 = Sf2File(sf2_file)

            # print(sf2.pretty_print())

            sf2_to_xrni = Sf2ToXrni(**vars(opts))

            for instrument_idx, sf2_instrument in enumerate(sf2.instruments):
                if sf2_instrument.is_sentinel():
                    continue

                if opts.instruments_index and instrument_idx not in opts.instruments_index:
                    continue

                if not opts.quiet:
                    print("Converting '{}'...".format(sf2_instrument.name), end='')

                # noinspection PyBroadException
                try:
                    renoise_instrument = RenoiseInstrument(template_filename=opts.template)
                    sf2_to_xrni.convert_instrument(sf2_instrument, renoise_instrument)

                    if not opts.no_expand_keymap:
                        expand_keymap(renoise_instrument)

                    output_filename = os.path.join(opts.output_dir or '',
                                                   '{}_{}.xrni'.format(instrument_idx, renoise_instrument.name))
                    # noinspection PyTypeChecker
                    renoise_instrument.save(output_filename, overwrite=opts.force)
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
