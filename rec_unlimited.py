#!/usr/bin/env python3
"""Create a recording with arbitrary duration.

The soundfile module (https://python-soundfile.readthedocs.io/)
has to be installed!

Modified by BNut to use the main.py script to get the target device

"""
import argparse
import tempfile
import queue
import sys
from time import sleep

import pydub.silence
import simpleaudio
import sounddevice as sd
import soundfile
import soundfile as sf
import numpy  # Make sure NumPy is loaded before it is used in the callback
from pydub import AudioSegment

from main import get_target_device

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
    print(sd.query_devices())
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
    with sf.SoundFile(args.filename, mode='x', samplerate=samplerate,
                      channels=channels, subtype=args.subtype) as file:
        with sd.InputStream(samplerate=samplerate, device=targetDevice['index'],
                            channels=channels, callback=callback):
            print('#' * 80)
            print('press Ctrl+C to stop the recording')
            print('#' * 80)
            while True:
                sleep(5)
                data = []
                while not q.empty():
                    data.append(q.get())

                print('Analyzing...' + len(data).__str__())
                # wave_obj = simpleaudio.WaveObject(data, 2, 2, 44100)
                # print(wave_obj)

                for chunk in data:
                    file.write(chunk)

except KeyboardInterrupt:
    print('\nRecording finished: ' + repr(args.filename))
    parser.exit(0)
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
