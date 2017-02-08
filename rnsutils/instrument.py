import logging
import math
import pkgutil
import pprint
from zipfile import ZipFile, ZIP_DEFLATED

import io
import os
from lxml import etree, objectify
from lxml.objectify import ObjectifiedElement

from .utils import guesstimate_audio_extension


def second_to_renoise_time(duration):
    return math.pow(duration / 60., 1 / 3.) if duration else None


def db_to_renoise_volume(volume):
    return math.exp(volume / 8.68) if volume else None


def _elements_equal(e1, e2):
    if e1 is None and e2 is None:
        return True
    if e1 is None or e2 is None:
        return False
    if e1.tag != e2.tag:
        return False
    if e1.text != e2.text:
        return False
    if e1.tail != e2.tail:
        return False
    if e1.attrib != e2.attrib:
        return False
    if len(e1) != len(e2):
        return False
    return all(_elements_equal(c1, c2) for c1, c2 in zip(e1.iterchildren(), e2.iterchildren()))


class RenoiseSample(ObjectifiedElement):
    pass


class RenoiseModulationSet(ObjectifiedElement):
    @property
    def ahdsr_attack(self):
        return self.Devices.SampleAhdsrModulationDevice.Attack.Value

    @ahdsr_attack.setter
    def ahdsr_attack(self, value):
        self.Devices.SampleAhdsrModulationDevice.Attack.Value = value

    @property
    def ahdsr_decay(self):
        return self.Devices.SampleAhdsrModulationDevice.Decay.Value

    @ahdsr_decay.setter
    def ahdsr_decay(self, value):
        self.Devices.SampleAhdsrModulationDevice.Decay.Value = value

    @property
    def ahdsr_hold(self):
        return self.Devices.SampleAhdsrModulationDevice.Hold.Value

    @ahdsr_hold.setter
    def ahdsr_hold(self, value):
        self.Devices.SampleAhdsrModulationDevice.Hold.Value = value

    @property
    def ahdsr_sustain(self):
        return self.Devices.SampleAhdsrModulationDevice.Sustain.Value

    @ahdsr_sustain.setter
    def ahdsr_sustain(self, value):
        self.Devices.SampleAhdsrModulationDevice.Sustain.Value = value

    @property
    def ahdsr_release(self):
        return self.Devices.SampleAhdsrModulationDevice.Release.Value

    @ahdsr_release.setter
    def ahdsr_release(self, value):
        self.Devices.SampleAhdsrModulationDevice.Release.Value = value

    @property
    def lp_cutoff(self):
        return self.Devices.SampleMixerModulationDevice.Cutoff.Value

    @lp_cutoff.setter
    def lp_cutoff(self, value):
        self.Devices.SampleMixerModulationDevice.Cutoff.Value = value


class RenoiseInstrument(object):
    OVERLAP_CYCLE = "Cycle"
    OVERLAP_ALL = "Play All"
    OVERLAP_RANDOM = "Random"

    LOOP_NONE = "Off"
    LOOP_FORWARD = "Forward"

    FILTER_NONE = 0
    FILTER_CLEAN_HP = 5
    FILTER_CLEAN_LP = 1

    def __init__(self, filename=None, template_filename="empty-31.xrni"):
        self.root = None
        self.sample_data = None
        self.sample_template = None
        self.sample_modulation_set = None

        if filename is not None:
            self.load(filename)
        else:
            try:
                self.load(template_filename)
            except IOError:
                self.load(io.BytesIO(pkgutil.get_data('rnsutils', 'data/{}'.format(template_filename))))

            self.extract_sample_template()
            self.extract_modulation_set_template()

    def extract_sample_template(self):

        self.sample_template = self.root.SampleGenerator.Samples.Sample[0]

        # delete all Sample node in the xml
        samples_node = self.root.SampleGenerator.Samples
        for original_sample in samples_node.Sample:
            samples_node.remove(original_sample)

        # delete all sample data
        self.sample_data = []

    def extract_modulation_set_template(self):

        self.modulation_set_template = self.root.SampleGenerator.ModulationSets.ModulationSet[0]

        # delete all modulation node in the xml
        modulation_set_node = self.root.SampleGenerator.ModulationSets
        for original_modulation_set in modulation_set_node.ModulationSet:
            modulation_set_node.remove(original_modulation_set)

    def load(self, filename):
        from .lookup import renoise_parser
        with ZipFile(filename) as z:
            self.root = etree.fromstring(z.read("Instrument.xml"), renoise_parser)
            self.sample_data = [z.read(sample_filename) for sample_filename in sorted(z.namelist()) if
                                sample_filename.startswith('SampleData')]

    def save(self, filename, overwrite=False, cleanup=True):

        if cleanup:
            self.cleanup()

        if os.path.isfile(filename) and not overwrite:
            logging.error("Destination file %s exists and overwrite was not forced", filename)
            return

        temp_filename = filename + '.part'

        with ZipFile(temp_filename, 'w', compression=ZIP_DEFLATED) as z:
            objectify.deannotate(self.root, cleanup_namespaces=True, xsi_nil=True)
            z.writestr("Instrument.xml", etree.tostring(self.root, pretty_print=True))
            for sample_idx, sample in enumerate(self.sample_data):
                z.writestr('SampleData/Sample{0:02} {1}.{2}'.format(sample_idx, self.root.SampleGenerator.Samples.
                                                                    Sample[sample_idx].Name,
                                                                    guesstimate_audio_extension(sample) or "wav"),
                           sample)

        os.rename(temp_filename, filename)

    @property
    def samples(self):
        return list(self.root.SampleGenerator.Samples.Sample)

    @property
    def name(self):
        return self.root.Name

    @name.setter
    def name(self, value):
        self.root.Name = value

    @property
    def comment(self):
        try:
            return "\n".join([comment.pyval for comment in self.root.GlobalProperties.Comments.Comment])
        except AttributeError:
            return None

    @comment.setter
    def comment(self, value):
        # noinspection PyPep8Naming
        E = objectify.E

        if 'Comments' not in self.root.GlobalProperties.getchildren():
            self.root.GlobalProperties.Comments = E.Comments()

        self.root.GlobalProperties.Comments.Comment = [E.Comment(line) for line in value.split("\n")]

    @comment.deleter
    def comment(self):
        del self.root.GlobalProperties.Comments

    @property
    def tags(self):
        try:
            return self.root.GlobalProperties.Tags.Tag
        except AttributeError:
            return None

    @tags.setter
    def tags(self, value):
        # noinspection PyPep8Naming
        E = objectify.E

        if 'Tags' not in self.root.GlobalProperties.getchildren():
            self.root.GlobalProperties.Tags = E.Tags()

        self.root.GlobalProperties.Tags.Tag = [E.Tag(tag) for tag in value]

    @tags.deleter
    def tags(self):
        del self.root.GlobalProperties.Tags

    def append_tag(self, tag):
        tags = self.tags
        if tags is None:
            self.tags = [tag]
        else:
            self.root.GlobalProperties.Tags.append(objectify.E.Tag(tag))

    def remove_tag(self, tag_to_remove):
        for tag_idx in range(len(self.root.GlobalProperties.Tags.getchildren())):
            tag = self.root.GlobalProperties.Tags.Tag[tag_idx]
            if tag.text == tag_to_remove:
                del self.root.GlobalProperties.Tags.Tag[tag_idx]
                return

    def cleanup(self):
        # ensure that key mapping remains in the limits of what renoise supports
        for sample in self.root.SampleGenerator.Samples.Sample:
            sample.Mapping.NoteEnd = min(119, sample.Mapping.NoteEnd)
            sample.Mapping.NoteStart = max(0, sample.Mapping.NoteStart)

        modulation_set_idx = 0
        while modulation_set_idx < len(self.root.SampleGenerator.ModulationSets.ModulationSet):

            lhs_modulation_set = self.root.SampleGenerator.ModulationSets.ModulationSet[modulation_set_idx]

            secondary_modulation_set_idx = modulation_set_idx + 1
            while secondary_modulation_set_idx < len(self.root.SampleGenerator.ModulationSets.ModulationSet):

                rhs_modulation_set = self.root.SampleGenerator.ModulationSets.ModulationSet[
                    secondary_modulation_set_idx]

                if _elements_equal(lhs_modulation_set, rhs_modulation_set):
                    self._replace_modulation_set(secondary_modulation_set_idx, modulation_set_idx)
                else:
                    secondary_modulation_set_idx += 1

            modulation_set_idx += 1

    def _replace_modulation_set(self, from_idx, to_idx):
        for sample in self.root.SampleGenerator.Samples.Sample:
            if sample.ModulationSetIndex > from_idx:
                sample.ModulationSetIndex = sample.ModulationSetIndex - 1
            elif sample.ModulationSetIndex == from_idx:
                sample.ModulationSetIndex = to_idx
        del self.root.SampleGenerator.ModulationSets.ModulationSet[from_idx]


if __name__ == "__main__":
    instrument = RenoiseInstrument('basic.xrni')
    pprint.pprint(instrument)
    pprint.pprint(instrument.samples)
    # s = instrument.samples[0]
    # print(s.foo())
    instrument.save('generated.xrni')
