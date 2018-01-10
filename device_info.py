import pyaudio
p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id {} - {}".format(i, p.get_device_info_by_host_api_device_index(0, i).get('name')))

for index in range(0, p.get_device_count()):
    dev = p.get_device_info_by_index(index)
    print(dev['name'])