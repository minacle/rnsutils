from lxml import etree
from lxml.objectify import ObjectifyElementClassLookup

from .instrument import RenoiseSample, RenoiseModulationSet


class RenoiseClassLookup(etree.CustomElementClassLookup):
    def __init__(self):
        super(RenoiseClassLookup, self).__init__(fallback=ObjectifyElementClassLookup())

    def lookup(self, node_type, document, namespace, name):
        if name == 'Sample':
            return RenoiseSample
        elif name == 'ModulationSet':
            return RenoiseModulationSet

        return None


renoise_parser = etree.XMLParser()
renoise_parser.setElementClassLookup(RenoiseClassLookup())
