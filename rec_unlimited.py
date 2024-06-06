#!/usr/bin/env python3
"""Create a recording with arbitrary duration.

The soundfile module (https://python-soundfile.readthedocs.io/)
has to be installed!

Modified by BNut to use the main.py script to get the target device

"""
import argparse
import audioop
import tempfile
import queue
import sys
from time import sleep

import pydub.silence
import simpleaudio
import sounddevice
import soundfile
import soundfile
import numpy  # Make sure NumPy is loaded before it is used in the callback
from pydub import AudioSegment

from main import get_target_device, RECORDING_THRESHOLD

assert numpy  # avoid "imported but unused" message (W0611)


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sounddevice.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    'filename', nargs='?', metavar='FILENAME',
    help='audio file to store recording to')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-t', '--subtype', type=str, help='sound file subtype (e.g. "PCM_24")')
args = parser.parse_args(remaining)

q = queue.Queue()


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())


targetDevice = get_target_device()
print(targetDevice)
# soundfile expects an int, sounddevice provides a float:
samplerate = int(targetDevice['defaultSampleRate'])
channels = targetDevice['maxInputChannels']

try:
    if args.filename is None:
        args.filename = tempfile.mktemp(prefix='piano_raw_',
                                        suffix='.wav', dir='piano_log')

    # Make sure the file is opened before recording anything:
    with soundfile.SoundFile(args.filename, mode='x', samplerate=samplerate,
                             channels=channels, subtype=args.subtype) as file:
        with sounddevice.InputStream(samplerate=samplerate, device=targetDevice['index'],
                                     channels=channels, callback=callback):
            print('#' * 80)
            print('press Ctrl+C to stop the recording')
            print('#' * 80)
            while True:
                sleep(3)
                data = []
                while q.qsize() > 8:
                    for _ in range(8):
                        data.append(q.get())

                bytes_data = numpy.array(data)
                loudness = audioop.rms(bytes_data, 4)
                if loudness > RECORDING_THRESHOLD:
                    print('Write Audio: ' + str(loudness))
                    for chunk in data:
                        file.write(chunk)
                else:
                    print('Skip Audio: ' + str(loudness))

except KeyboardInterrupt:
    print('\nRecording finished: ' + repr(args.filename))
    parser.exit(0)
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
