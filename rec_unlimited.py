#!/usr/bin/env python3
import argparse
import audioop
import tempfile
import queue
import sys
from time import sleep

import sounddevice
import soundfile
import numpy  # Make sure NumPy is loaded before it is used in the callback

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


def create_file_name():
    return tempfile.mktemp(prefix='piano_raw_', suffix='.wav', dir='piano_log')


def write_to_file(file, queuedData):
    for timeChunk in queuedData:
        for chunk in timeChunk:
            file.write(chunk)


def start_recording_agent():
    silentCount = 0
    loudCount = 0
    queuedData = []
    recording = False

    def reset_recording():
        nonlocal silentCount
        silentCount = 0
        nonlocal loudCount
        loudCount = 0
        queuedData.clear()
        nonlocal recording
        recording = False

    # Start recording to queue "q"
    with sounddevice.InputStream(
            samplerate=samplerate,
            device=targetDevice['index'],
            channels=channels,
            callback=callback,
    ):
        # Loopies! \( ^_^)/
        while True:
            sleep(3)  # Chill for three seconds, gotta record stuff at *some* point...
            data = []
            while q.qsize() > 8:
                for _ in range(8):
                    data.append(q.get())

            bytes_data = numpy.array(data)
            loudness = audioop.rms(bytes_data, 4)

            loudNow = loudness > RECORDING_THRESHOLD
            file: soundfile.SoundFile

            if loudNow:
                print('Loud Audio: ' + str(loudness))
                loudCount += 1
                silentCount = 0
            else:
                print('Silent Audio: ' + str(loudness))
                silentCount += 1

            if loudCount == 0:
                print('Standby...')
                if len(queuedData) == 2:
                    queuedData.remove(queuedData[0])
                silentCount = 0
            elif loudCount > 0 and recording is False:
                filename = create_file_name()
                print('Starting new file: ' + filename)
                file = soundfile.SoundFile(filename, mode='x', samplerate=samplerate, channels=channels,
                                           subtype=args.subtype)
                recording = True

            queuedData.append(bytes_data)

            if recording:
                for timeChunk in queuedData:
                    for chunk in timeChunk:
                        file.write(chunk)
                queuedData.clear()

            if silentCount >= 2:
                print('Closing recording: ' + filename)
                file.close()
                reset_recording()


start_recording_agent()
