import pyaudio

TARGET_DEVICE_NAME = "Mikrofon (3- USB Audio CODEC )"
TARGET_DIR = "piano_log"
NORMALIZATION_LEVEL = -26  # dBFS
RECORDING_THRESHOLD = 1000  # Threshold for loudness - 1000 is relatively low because my line signal is very clean.
RECORDING_INTERVAL_S = 3  # Time to wait between recording intervals and checking for loudness
MINIMUM_RECORDING_INTERVALS: int = 3  # How many intervals need to be loud before starting a new file
RETAIN_INTERVALS = 1  # How many intervals of silence to retain before starting a new file
CLOSING_SILENT_INTERVALS = 1  # How many intervals of silence to wait before closing the file

pyAudio = pyaudio.PyAudio()


def get_target_device():
    hostInfo = pyAudio.get_host_api_info_by_index(0)
    deviceCount = hostInfo.get('deviceCount')
    for i in range(deviceCount):
        device = pyAudio.get_device_info_by_host_api_device_index(0, i)
        if device.get('name') == TARGET_DEVICE_NAME:
            return device


if __name__ == "__main__":
    print(get_target_device())
