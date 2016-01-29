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


def encode_audio_file(sample_content, encoding):
    if encoding == ENCODING_FLAC:
        in_filename = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        out_filename = tempfile.NamedTemporaryFile(suffix='.flac', delete=False).name
        try:
            with open(in_filename, "wb") as infile:
                infile.write(sample_content)
            subprocess.check_call(["flac", in_filename, "-f", "-o", out_filename])
            with open(out_filename, "rb") as outfile:
                return outfile.read()
        except:
            logging.exception("Error while converting to flac")
        finally:
            os.remove(in_filename)
            os.remove(out_filename)

    elif encoding == ENCODING_OGG:
        in_filename = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        out_filename = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False).name
        try:
            with open(in_filename, "wb") as infile:
                infile.write(sample_content)
            subprocess.check_call(["oggenc", in_filename, "-o", out_filename])
            with open(out_filename, "rb") as outfile:
                return outfile.read()
        except:
            logging.exception("Error while converting to ogg")
        finally:
            os.remove(in_filename)
            os.remove(out_filename)

    return sample_content
