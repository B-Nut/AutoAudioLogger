#!/usr/bin/env python3
import queue
import sys
from time import sleep

import sounddevice
import soundfile
from pynormalize import pynormalize

from main import CLOSING_SILENT_INTERVALS, RETAIN_INTERVALS, \
    RECORDING_INTERVAL_S, MINIMUM_RECORDING_INTERVALS, TARGET_DIR, NORMALIZATION_LEVEL, is_loud, create_file_name


def start_agent(targetDevice, verbose=False):
    deviceIndex = targetDevice['index']
    sampleRate = int(targetDevice['defaultSampleRate'])
    channels = targetDevice['maxInputChannels']
    arrayLength = 4 * channels  # Length of a single audio sample in Byte. 4 Bytes per channel.

    rawInput = queue.Queue()
    queuedIntervals = []

    def remove_oldest_invervals():
        while len(queuedIntervals) > RETAIN_INTERVALS:
            queuedIntervals.pop(0)

    def remove_last_interval():
        if len(queuedIntervals) > 0:
            queuedIntervals.pop()

    loudCount: int
    silenceDuration: int  # in Intervals
    writtenIntervals: int
    writing: bool

    def reset_recording():
        nonlocal silenceDuration
        silenceDuration = 0
        nonlocal loudCount
        loudCount = 0
        nonlocal writtenIntervals
        writtenIntervals = 0
        nonlocal writing
        writing = False
        print('Standby...')
        remove_oldest_invervals()

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        rawInput.put(indata.copy())

    file: soundfile.SoundFile  # Holds the current recording file, if any
    reset_recording()  # Initialize the standby recording state
    # Start recording to queue "rawInput"
    with sounddevice.InputStream(
            samplerate=sampleRate,
            device=deviceIndex,
            channels=channels,
            callback=callback,
    ):
        # Loopies! \( ^_^)/
        # This loop runs independently to the recording callback, so we can work without time pressure.
        while True:
            sleep(RECORDING_INTERVAL_S)  # Chill for an interval seconds, gotta record stuff at *some* point...
            data = []
            while rawInput.qsize() > arrayLength:
                for _ in range(arrayLength):  # Takes only complete audio chunks of data
                    data.append(rawInput.get())
            queuedIntervals.append(data)

            if is_loud(data, arrayLength):
                loudCount += 1
                silenceDuration = 0
            else:
                silenceDuration += 1

            if loudCount == 0:
                # Standby mode
                remove_oldest_invervals()  # Retains the set amount of intervals
                silenceDuration = 0

            if silenceDuration > RETAIN_INTERVALS:
                # Active, but dropping silent intervals
                remove_last_interval()

            if (loudCount >= MINIMUM_RECORDING_INTERVALS) & (writing is False):
                filename = create_file_name()
                print('Starting recording to new file: ' + filename)
                file = soundfile.SoundFile(filename, mode='x', samplerate=sampleRate, channels=channels)
                writing = True

            if silenceDuration >= CLOSING_SILENT_INTERVALS:
                if writing:
                    print('Closing recording: ' + filename)
                    file.close()
                    pynormalize.process_files([filename], NORMALIZATION_LEVEL, TARGET_DIR)
                reset_recording()

            if writing:
                for timeInterval in queuedIntervals:
                    for data in timeInterval:
                        file.write(data)
                    writtenIntervals += 1
                queuedIntervals.clear()

            if (loudCount > 0) & verbose:
                intervalCount = len(queuedIntervals) + writtenIntervals
                print('---- Recorder ----' +
                      '\nLoud: ' + str(loudCount) + '/' + str(MINIMUM_RECORDING_INTERVALS) + ' interval(s)' +
                      '\nOn file: ' + str(writtenIntervals) + '/' + str(intervalCount) + ' interval(s)' +
                      '\nSilence: ' + str(silenceDuration) + '/' + str(CLOSING_SILENT_INTERVALS) + ' interval(s)' +
                      '\n------------------')
