import atexit
import logging
import os
import sys
from datetime import datetime
from time import sleep
from typing import Mapping

import numpy
import pyaudio

import auto_recorder

TARGET_DEVICE_NAME = "USB Audio CODEC"
TARGET_DIR = "piano_log"  # Directory to save the normalized mp3 recordings
RAW_DIR = "raw_audio"  # Directory to save the raw recordings
RECORDING_THRESHOLD = 0.01  # Used to determine if a recorded interval is loud
RECORDING_INTERVAL_S = 3  # Time of recorded intervals, that are checked for loudness
MINIMUM_RECORDING_INTERVALS: int = 10  # How many intervals need to be loud before starting a new file
RETAIN_INTERVALS = 1  # How many intervals of silence to retain before and after all recordings
CLOSING_SILENT_INTERVALS = 2  # How many intervals of silence to wait before closing the file

ARTIST = "BNut"
ALBUM = "Piano Log"

pyAudio = pyaudio.PyAudio()


def get_target_device() -> Mapping[str, str | int | float]:
    while True:
        hostInfo = pyAudio.get_host_api_info_by_index(0)
        deviceCount = hostInfo.get('deviceCount')
        for i in range(deviceCount):
            device = pyAudio.get_device_info_by_host_api_device_index(0, i)
            if TARGET_DEVICE_NAME in device.get('name'):
                logging.info("Recording device: " + str(device.get('name')))
                return device
        logging.info("No device containing '" + TARGET_DEVICE_NAME + "' found. Trying again in 10 seconds.")
        sleep(10)


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
    return datetime.strftime(datetime.now(), '%Y%m%d_%H-%M-%S')  # 20210901_12-34-56


def date_string() -> str:
    return datetime.strftime(datetime.now(), '%Y%m%d')


def nice_date_string() -> str:
    return datetime.strftime(datetime.now(), '%B %Y')


def create_file_name() -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    return os.path.join(RAW_DIR, time_string() + '_audio_log' + '.wav')


def initialize_logging():
    logging.basicConfig(level=logging.INFO, filename=os.path.join('logs', time_string() + '_auto_recorder.log'),
                        filemode='a+', format="%(asctime)-15s %(levelname)-8s %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


if __name__ == "__main__":
    atexit.register(auto_recorder.close_file)
    initialize_logging()
    auto_recorder.start_agent(get_target_device())
