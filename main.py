import os
from datetime import datetime
from typing import Mapping

import numpy
import pyaudio

import auto_recorder

TARGET_DEVICE_NAME = "Mikrofon (3- USB Audio CODEC )"
TARGET_DIR = "piano_log"  # Directory to save the normalized recordings
RAW_DIR = "raw_audio"  # Directory to save the raw recordings. Raw files are overwritten if this is set to TARGET_DIR
TARGET_DIR = "piano_log"  # Directory to save the normalized mp3 recordings
RAW_DIR = "raw_audio"  # Directory to save the raw recordings
RECORDING_THRESHOLD = 0.01  # Used to determine if a recorded interval is loud
RECORDING_INTERVAL_S = 3  # Time of recorded intervals, that are checked for loudness
MINIMUM_RECORDING_INTERVALS: int = 3  # How many intervals need to be loud before starting a new file
RETAIN_INTERVALS = 1  # How many intervals of silence to retain before and after all recordings
CLOSING_SILENT_INTERVALS = 10  # How many intervals of silence to wait before closing the file

pyAudio = pyaudio.PyAudio()


def get_target_device() -> Mapping[str, str | int | float]:
    hostInfo = pyAudio.get_host_api_info_by_index(0)
    deviceCount = hostInfo.get('deviceCount')
    for i in range(deviceCount):
        device = pyAudio.get_device_info_by_host_api_device_index(0, i)
        if device.get('name') == TARGET_DEVICE_NAME:
            return device


def loudness(data) -> float:
    try:
        # This is so dumb, but it works for my clean signal.
        # If your signal is more noisy, I'm interested in your solution.
        return numpy.array(data).max()
    except ValueError:  # On Unix, the data is the same, but nested weirdly.
        return loudness(flatten(data))


def flatten(data):
    try:
        return [beep for dat in data for beep in dat]  # Take dat from data, then beep from dat.
    except TypeError:  # Elements in data are not iterable, no nested data to flatten.
        return data


def is_loud(data) -> bool:
    return loudness(data) > RECORDING_THRESHOLD


def time_string() -> str:
    return datetime.strftime(datetime.now(), '%Y%m%d_%H-%M-%S')


def create_file_name() -> str:
    return os.path.join(RAW_DIR, time_string() + '_audio_log' + '.wav')


if __name__ == "__main__":
    try:
        auto_recorder.start_agent(get_target_device(), verbose=True)
    except KeyboardInterrupt:
        auto_recorder.close_file()
        print('Interrupted.')
