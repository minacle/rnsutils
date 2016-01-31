import logging
import subprocess

import os
import tempfile


def guesstimate_audio_extension(data):
    if len(data) > 8 and data[0:8] == b'fLaC\0\0\0\x22':
        return "flac"
    if len(data) > 3 and data[0:3] == b'Ogg':
        return "ogg"
    return None


ENCODING_NONE = "none"
ENCODING_FLAC = "flac"
ENCODING_OGG = "ogg"


def _call_encoder(func):
    def inner(sample_content):
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
    return subprocess.Popen(["flac", in_filename, "-f", "-o", out_filename], stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE)


@_call_encoder
def _encode_ogg(in_filename, out_filename):
    return subprocess.Popen(["oggenc", in_filename, "-o", out_filename], stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE)


def encode_audio_file(sample_content, encoding):
    if encoding == ENCODING_FLAC:
        return _encode_flac(sample_content)
    elif encoding == ENCODING_OGG:
        return _encode_ogg(sample_content)

    return sample_content
