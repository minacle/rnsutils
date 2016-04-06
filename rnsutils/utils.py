"""project wide utilities, notably audio format guessing and encoding"""

import logging
import subprocess

import os
import tempfile


def guesstimate_audio_extension(data):
    """:arg data audio file content
    :return file format extension guessed from file content"""

    if len(data) > 8 and data[0:8] == b'fLaC\0\0\0\x22':
        return "flac"
    if len(data) > 3 and data[0:3] == b'Ogg':
        return "ogg"
    return None


ENCODING_NONE = "none"
ENCODING_FLAC = "flac"
ENCODING_OGG = "ogg"


def _call_encoder(func):
    """decorator for creating a temporary file, calling an encoder and cleaning temporary files"""

    def inner(sample_content):
        """actual wrapping function to create and clean temporary files around audio encoding"""
        out_format = guesstimate_audio_extension(sample_content)
        in_filename = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        out_filename = tempfile.NamedTemporaryFile(suffix='.{}'.format(out_format), delete=False).name
        try:
            with open(in_filename, "wb") as infile:
                infile.write(sample_content)

            func(in_filename, out_filename).communicate()

            with open(out_filename, "rb") as outfile:
                return outfile.read()
        except:
            logging.exception("Error while converting to %s", out_format)
        finally:
            os.remove(in_filename)
            os.remove(out_filename)

    return inner


@_call_encoder
def _encode_flac(in_filename, out_filename):
    """encode :arg in_filename into :arg out_filename using flac"""
    return subprocess.Popen(["flac", in_filename, "-f", "-o", out_filename], stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE)


@_call_encoder
def _encode_ogg(in_filename, out_filename):
    """encode :arg in_filename into :arg out_filename using ogg vorbis"""
    return subprocess.Popen(["oggenc", in_filename, "-o", out_filename], stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE)


def encode_audio_file(sample_content, encoding):
    """encode :arg sample_content as audio file content into :arg encoding format"""
    if encoding == ENCODING_FLAC:
        return _encode_flac(sample_content)
    elif encoding == ENCODING_OGG:
        return _encode_ogg(sample_content)

    return sample_content


def expand_keymap(instrument):
    """expand zones 'horizontally', ie keyranges, to cover as much as possible the whole key mapping"""
    for velocity in range(0, 256):

        minimum_note_start = None
        maximum_note_end = None

        # for each velocity, detect extremum zones
        for sample_idx, sample in enumerate(instrument.root.SampleGenerator.Samples.Sample):

            # only consider zones matching the current velocity
            if not (sample.Mapping.VelocityStart <= velocity <= sample.Mapping.VelocityEnd):
                continue

            if minimum_note_start is None or sample.Mapping.NoteStart < minimum_note_start:
                minimum_note_start = sample.Mapping.NoteStart

            if maximum_note_end is None or sample.Mapping.NoteEnd > maximum_note_end:
                maximum_note_end = sample.Mapping.NoteEnd

        # if for the current velocity, we already span the whole range, no need to adapt any zone
        if minimum_note_start == 0 and maximum_note_end >= 119:
            continue

        # else, extends every zone part being an extremum (there can be more than one for layered zones)
        for sample in instrument.root.SampleGenerator.Samples.Sample:

            if not (sample.Mapping.VelocityStart <= velocity <= sample.Mapping.VelocityEnd):
                continue

            if sample.Mapping.NoteStart == minimum_note_start:
                logging.debug("Changing velocity range from %d-%d to %d-%d", sample.Mapping.NoteStart,
                              sample.Mapping.NoteEnd, 0, sample.Mapping.NoteEnd)
                sample.Mapping.NoteStart = 0

            if sample.Mapping.NoteEnd == maximum_note_end:
                logging.debug("Changing velocity range from %d-%d to %d-%d", sample.Mapping.NoteStart,
                              sample.Mapping.NoteEnd, sample.Mapping.NoteStart, 119)
                sample.Mapping.NoteEnd = 119
