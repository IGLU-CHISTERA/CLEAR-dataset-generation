import numpy as np


def pydub_audiosegment_to_float_array(audio_segment, n_bytes):
    """Convert an integer buffer to floating point values.
    This is primarily useful when loading integer-valued wav data
    into numpy arrays.

    Taken from https://librosa.github.io/librosa/_modules/librosa/util/utils.html#buf_to_float

    FIXME : This will only work for mono audio segment because of the way data is ordered in a pydub audio segment
    FIXME : See https://groups.google.com/d/msg/librosa/XWae4PdbXuk/4LjHK3d4BAAJ for a fix
    """

    raw_data = audio_segment.get_array_of_samples()

    # Invert the scale of the data
    scale = 1. / float(1 << ((8 * n_bytes) - 1))

    # Construct the format string
    fmt = '<i{:d}'.format(n_bytes)

    # Rescale and format the data buffer
    return scale * np.frombuffer(raw_data, fmt).astype(np.float32)


def midi_pitch_to_musical_note(self, midi_value):
    note = self.notes[midi_value % 12]
    octave = int(midi_value/12) - 1

    return note + str(octave)