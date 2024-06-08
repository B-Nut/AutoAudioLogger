import audioop
import os
from datetime import datetime
from typing import Mapping

import numpy
import pyaudio
import pydub

import auto_recorder

TARGET_DEVICE_NAME = "Mikrofon (3- USB Audio CODEC )"
TARGET_DIR = "piano_log"
NORMALIZATION_LEVEL = -21  # dBFS
RECORDING_THRESHOLD = 1000  # Threshold for loudness - 1000 is relatively low because my line signal is very clean.
RECORDING_INTERVAL_S = 3  # Time to wait between recording intervals and checking for loudness
MINIMUM_RECORDING_INTERVALS: int = 3  # How many intervals need to be loud before starting a new file
RETAIN_INTERVALS = 1  # How many intervals of silence to retain before and after all recordings.
CLOSING_SILENT_INTERVALS = 5  # How many intervals of silence to wait before closing the file

pyAudio = pyaudio.PyAudio()


def get_target_device() -> Mapping[str, str | int | float]:
    hostInfo = pyAudio.get_host_api_info_by_index(0)
    deviceCount = hostInfo.get('deviceCount')
    for i in range(deviceCount):
        device = pyAudio.get_device_info_by_host_api_device_index(0, i)
        if device.get('name') == TARGET_DEVICE_NAME:
            return device


def is_loud(data, arrayLength, verbose=False) -> bool:
    loudness = audioop.findmax(numpy.array(data), int(arrayLength / 2))
    isLoud = loudness > RECORDING_THRESHOLD
    if verbose:
        print('Loudness: ' + str(loudness) + '\nSound detected: ' + str(isLoud))
    return loudness > RECORDING_THRESHOLD


def is_loud_experimental(data) -> bool:
    seq = pydub.AudioSegment(numpy.array(data), frame_rate=44100, sample_width=2, channels=2)
    print(seq.dBFS)  # Actually DBFs?!


def create_file_name():
    timestring = datetime.strftime(datetime.now(), '%Y%m%d_%H-%M-%S')
    return os.path.join('raw_audio', timestring + '_audio_log' + '.wav')


if __name__ == "__main__":
    targetDevice = get_target_device()
    print(targetDevice)
    auto_recorder.start_agent(targetDevice, verbose=True)
