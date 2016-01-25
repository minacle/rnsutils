def guesstimate_audio_extension(data):
    if len(data) > 8 and data[0:8] == b'fLaC\0\0\0\x22':
        return "flac"
    return None
