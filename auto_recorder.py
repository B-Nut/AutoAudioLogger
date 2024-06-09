import queue
import sys
from time import sleep

import pydub
import sounddevice
import soundfile
from soundfile import SoundFile
from pynormalize import pynormalize

from main import CLOSING_SILENT_INTERVALS, RETAIN_INTERVALS, \
    RECORDING_INTERVAL_S, MINIMUM_RECORDING_INTERVALS, TARGET_DIR, NORMALIZATION_LEVEL, is_loud, create_file_name, \
    RECORDING_THRESHOLD, time_string, loudness, RAW_DIR

file: SoundFile  # Holds the current recording file, if any
fileOpen: bool = False  # True if a file is currently being open and recording


def new_soundfile(filename: str, sampleRate: int, channels: int):
    global file
    global fileOpen
    print('Starting recording to new file: ' + filename)
    file = soundfile.SoundFile(filename, mode='x', samplerate=sampleRate, channels=channels)
    fileOpen = True


def close_file():
    global fileOpen
    if fileOpen:
        print('Closing recording: ' + file.name)
        file.close()

        # Post-processing: Normalize and convert to mp3
        originalAudio = pydub.AudioSegment.from_wav(file.name)
        normalizedAudio = pydub.effects.normalize(originalAudio)
        exportFileName = file.name.replace('.wav', '.mp3').replace(RAW_DIR, TARGET_DIR)
        normalizedAudio.export(exportFileName, format='mp3', bitrate='320k')
        print('Exported to: ' + exportFileName)

        fileOpen = False


def start_agent(targetDevice, verbose=False):
    deviceIndex = targetDevice['index']
    sampleRate = int(targetDevice['defaultSampleRate'])
    channels = targetDevice['maxInputChannels']
    arrayLength = 4 * channels  # Length of a single audio sample in Byte. 4 Bytes per channel.

    rawInput = queue.Queue()
    queuedIntervals = []

    def remove_oldest_intervals():
        while len(queuedIntervals) > RETAIN_INTERVALS:
            queuedIntervals.pop(0)

    def remove_last_interval():
        if len(queuedIntervals) > 0:
            queuedIntervals.pop()

    loudCount: int = 0
    silenceDuration: int = 0  # in Intervals
    writtenIntervals: int = 0

    def reset_recorder():
        nonlocal loudCount
        nonlocal silenceDuration
        nonlocal writtenIntervals
        loudCount = 0
        silenceDuration = 0
        writtenIntervals = 0
        remove_oldest_intervals()
        print('Standby...')

    reset_recorder()  # Mainly called here to initially print the "Standby..." recording state >.<

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        rawInput.put(indata.copy())

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

            if is_loud(data):
                loudCount += 1
                silenceDuration = 0
            else:
                silenceDuration += 1

            if loudCount == 0:
                # Standby mode
                remove_oldest_intervals()  # Retains the set amount of intervals
                silenceDuration = 0

            if silenceDuration > RETAIN_INTERVALS:
                # Active, but dropping silent intervals
                remove_last_interval()

            if (loudCount >= MINIMUM_RECORDING_INTERVALS) & (fileOpen is False):
                new_soundfile(create_file_name(), sampleRate, channels)

            if silenceDuration >= CLOSING_SILENT_INTERVALS:
                close_file()
                reset_recorder()

            if fileOpen:  # Write queued intervals to the file
                for timeInterval in queuedIntervals:
                    for data in timeInterval:
                        file.write(data)
                    writtenIntervals += 1
                queuedIntervals.clear()

            if (loudCount > 0) & verbose:
                intervalCount = len(queuedIntervals) + writtenIntervals
                measured = loudness(data)
                fileString = 'File ' + file.name + ': ' if fileOpen else 'No File Open: '
                print('---- Recorder ----' +
                      '\nTime: ' + time_string() +
                      '\nLoud: ' + str(is_loud(data)) + ' (' + str(measured) + '/' + str(RECORDING_THRESHOLD) + ')' +
                      '\nCaptured: ' + str(loudCount) + '/' + str(MINIMUM_RECORDING_INTERVALS) + ' loud interval(s)' +
                      '\n' + fileString + str(writtenIntervals) + '/' + str(intervalCount) + ' interval(s)' +
                      '\nSilence: ' + str(silenceDuration) + '/' + str(CLOSING_SILENT_INTERVALS) + ' interval(s)' +
                      '\n------------------')
