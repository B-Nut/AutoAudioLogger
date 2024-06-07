#!/usr/bin/env python3
import audioop
import datetime
import os.path
import queue
import sys
from time import sleep

import sounddevice
import soundfile
import numpy  # Make sure NumPy is loaded before it is used in the callback
from pynormalize import pynormalize

from main import get_target_device, RECORDING_THRESHOLD, CLOSING_SILENT_INTERVALS, RETAIN_INTERVALS, \
    RECORDING_INTERVAL_S, MINIMUM_RECORDING_INTERVALS, TARGET_DIR, NORMALIZATION_LEVEL

assert numpy  # avoid "imported but unused" message (W0611)

targetDevice = get_target_device()
print(targetDevice)
# soundfile expects an int, sounddevice provides a float:
samplerate = int(targetDevice['defaultSampleRate'])
channels = targetDevice['maxInputChannels']
arrayLength = 4 * channels


def create_file_name():
    timestring = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d_%H-%M-%S')
    return os.path.join(TARGET_DIR, timestring + '_audio_log' + '.wav')


def start_recording_agent():
    q = queue.Queue()
    queuedIntervals = []

    silentCount: int = 0
    loudCount: int = 0

    file: soundfile.SoundFile
    writing = False

    def flush_queue():
        while len(queuedIntervals) > RETAIN_INTERVALS:
            queuedIntervals.remove(queuedIntervals[0])

    def reset_recording():
        nonlocal silentCount
        silentCount = 0
        nonlocal loudCount
        loudCount = 0
        nonlocal writing
        writing = False
        flush_queue()

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    # Start recording to queue "q"
    with sounddevice.InputStream(
            samplerate=samplerate,
            device=targetDevice['index'],
            channels=channels,
            callback=callback,
    ):
        # Loopies! \( ^_^)/
        # This loop runs independently to the recording loop, so we can work without time pressure.
        while True:
            sleep(RECORDING_INTERVAL_S)  # Chill for an interval seconds, gotta record stuff at *some* point...
            data = []
            while q.qsize() > arrayLength:
                for _ in range(arrayLength):
                    data.append(q.get())
            queuedIntervals.append(data)

            loudness = audioop.findmax(numpy.array(data), int(arrayLength / 2))

            if loudness > RECORDING_THRESHOLD:
                print('Loud Audio: ' + str(loudness))
                loudCount += 1
                silentCount = 0
            else:
                print('Silent Audio: ' + str(loudness))
                silentCount += 1

            if loudCount == 0:
                print('Standby...')
                flush_queue()
                silentCount = 0
            else:
                if (loudCount >= MINIMUM_RECORDING_INTERVALS) & (writing is False):
                    filename = create_file_name()
                    print('Writing to new file: ' + filename)
                    file = soundfile.SoundFile(filename, mode='x', samplerate=samplerate, channels=channels)
                    writing = True
                print('Recorded ' + str(loudCount) + ' loud interval(s).\nWriting: ' + str(writing))

            if silentCount > CLOSING_SILENT_INTERVALS:
                if writing:
                    print('Closing recording: ' + filename)
                    file.close()
                    pynormalize.process_files([filename], NORMALIZATION_LEVEL, TARGET_DIR)
                reset_recording()

            if writing:
                for timeInterval in queuedIntervals:
                    for data in timeInterval:
                        file.write(data)
                queuedIntervals.clear()


start_recording_agent()
