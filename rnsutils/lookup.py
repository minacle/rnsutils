"""lookup for mapping xml elements into custom python wrappers"""
from lxml import etree
from lxml.objectify import ObjectifyElementClassLookup

from .instrument import RenoiseSample, RenoiseModulationSet


class RenoiseClassLookup(etree.CustomElementClassLookup):
    """mapping class for xml element to python class"""

    def __init__(self):
        super(RenoiseClassLookup, self).__init__(fallback=ObjectifyElementClassLookup())

    def lookup(self, node_type, document, namespace, name):
        """mapping method for xml element to python class"""
        if name == 'Sample':
            return RenoiseSample
        elif name == 'ModulationSet':
            return RenoiseModulationSet

        return None


renoise_parser = etree.XMLParser()
renoise_parser.setElementClassLookup(RenoiseClassLookup())
