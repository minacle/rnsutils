import pkgutil
import pprint
from zipfile import ZipFile, ZIP_DEFLATED

import io
from lxml import etree, objectify
from lxml.objectify import ObjectifiedElement

from .utils import guesstimate_audio_extension


class RenoiseSample(ObjectifiedElement):
    pass


class RenoiseModulationSet(ObjectifiedElement):
    @property
    def adhsr_release(self):
        return self.Devices.SampleAhdsrModulationDevice.Release.Value

    @adhsr_release.setter
    def adhsr_release(self, value):
        self.Devices.SampleAhdsrModulationDevice.Release.Value = value

    @property
    def lp_cutoff(self):
        return self.Devices.SampleMixerModulationDevice.Cutoff.Value

    @lp_cutoff.setter
    def lp_cutoff(self, value):
        self.Devices.SampleMixerModulationDevice.Cutoff.Value = value


class RenoiseInstrument(object):
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
            except FileNotFoundError:
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

    def save(self, filename):
        with ZipFile(filename, 'w', compression=ZIP_DEFLATED) as z:
            objectify.deannotate(self.root, cleanup_namespaces=True, xsi_nil=True)
            z.writestr("Instrument.xml", etree.tostring(self.root, pretty_print=True))
            for sample_idx, sample in enumerate(self.sample_data):
                z.writestr('SampleData/Sample{0:02} {1}.{2}'.format(sample_idx, self.root.SampleGenerator.Samples.
                                                                    Sample[sample_idx].Name,
                                                                    guesstimate_audio_extension(sample) or "wav"),
                           sample)

    @property
    def samples(self):
        return list(self.root.SampleGenerator.Samples.Sample)

    @property
    def name(self):
        return self.root.Name

    @name.setter
    def name(self, value):
        self.root.Name = value


if __name__ == "__main__":
    instrument = RenoiseInstrument('basic.xrni')
    pprint.pprint(instrument)
    pprint.pprint(instrument.samples)
    #  s = instrument.samples[0]
    # print(s.foo())
    instrument.save('generated.xrni')
