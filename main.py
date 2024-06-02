from pydub import AudioSegment, silence
import pyaudio
import sounddevice

TARGET_DEVICE_NAME = "Mikrofon (USB Audio), MME"
# TARGET_DEVICE_NAME = "Mikrofon (3- USB Audio CODEC ), MME"

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 2
WAVE_OUTPUT_FILENAME = "output.wav"

pyAudio = pyaudio.PyAudio()


def main():
    print_input_devices()


def set_device():
    hostInfo = pyAudio.get_host_api_info_by_index(0)
    deviceCount = hostInfo.get('deviceCount')
    myDevice = None
    for i in range(deviceCount):
        device = pyAudio.get_device_info_by_host_api_device_index(0, i)
        if device.get('name') == TARGET_DEVICE_NAME:
            sounddevice.default.device = myDevice['index']
            break


def record_audio():
    targetDevice = sounddevice.query_devices(TARGET_DEVICE_NAME)
    print(targetDevice)
    # sounddevice.default.device = targetDevice['index']
    recording = []
    sounddevice.rec(data=recording, frames=RATE * RECORD_SECONDS, samplerate=RATE, channels=CHANNELS, blocking=True)
    # sounddevice.play(recording, frames=RATE * RECORD_SECONDS, samplerate=RATE, channels=CHANNELS, blocking=True)


def print_input_devices():
    print(sounddevice.query_devices())


if __name__ == "__main__":
    main()
