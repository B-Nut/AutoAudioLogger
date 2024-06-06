#!/usr/bin/env python3
import audioop
import tempfile
import queue
import sys
from time import sleep

import sounddevice
import soundfile
import numpy  # Make sure NumPy is loaded before it is used in the callback

from main import get_target_device, RECORDING_THRESHOLD, CLOSING_SILENT_INTERVALS, RETAIN_INTERVALS, \
    RECORDING_INTERVAL_S, MINIMUM_RECORDING_INTERVALS

assert numpy  # avoid "imported but unused" message (W0611)

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
arrayLength = 4 * channels


def create_file_name():
    return tempfile.mktemp(prefix='piano_raw_', suffix='.wav', dir='piano_log')


def write_to_file(file, queuedData):
    for timeChunk in queuedData:
        for chunk in timeChunk:
            file.write(chunk)


def start_recording_agent():
    silentCount: int = 0
    loudCount: int = 0
    queuedData = []
    recording = False
    file: soundfile.SoundFile

    def flush_queue():
        while len(queuedData) > RETAIN_INTERVALS:
            queuedData.remove(queuedData[0])

    def reset_recording():
        nonlocal silentCount
        silentCount = 0
        nonlocal loudCount
        loudCount = 0
        nonlocal recording
        recording = False
        flush_queue()

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

            bytes_data = numpy.array(data)
            loudness = audioop.rms(bytes_data, int(arrayLength / 2))
            queuedData.append(bytes_data)

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
                if (loudCount >= MINIMUM_RECORDING_INTERVALS) & (recording is False):
                    filename = create_file_name()
                    print('Writing to new file: ' + filename)
                    file = soundfile.SoundFile(filename, mode='x', samplerate=samplerate, channels=channels)
                    recording = True
                print('Recorded' + str(loudCount) + ' interval(s).\nWriting: ' + str(recording))

            if silentCount > CLOSING_SILENT_INTERVALS:
                if recording:
                    print('Closing recording: ' + filename)
                    file.close()
                reset_recording()

            if recording:
                for timeChunk in queuedData:
                    for chunk in timeChunk:
                        file.write(chunk)
                queuedData.clear()


start_recording_agent()
