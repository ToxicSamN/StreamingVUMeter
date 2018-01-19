#!/usr/bin/python
"""
 Streaming Meter
 Author: Sammy Shuck
 Python Compatibility: Python 3.2, 3.4, 3.5, 3.6.4
 Requirements: python-pyaudio, python-pygame, Linux OS, mplayer
 This program is designed specifically for Raspberry Pi 3 Model B for a client radio
 station who provides their own
 streaming services.
"""

import sys
import audioop
import math
import time
import array
import xml.etree.ElementTree as ET
import threading
import requests
import pygame
import pyaudio
from requests.exceptions import ConnectionError
from pyradio import StationInfo, StreamPlayer

# ToDo: Add arg parser function
# ToDo: Add logging
# This program can utilize some argument parsers to accept cmdline input as well as
# being able to pares a config file

# setup code
pygame.init()
pygame.mixer.quit()  # stops unwanted audio output on some computers


# CLASS DEFINITIONS
class ColorPicker:
    """ Used for pygame coloring to make it easier to pick a color by name instead of color code"""
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 50, 50)
    YELLOW = (255, 255, 0)
    GREEN = (0, 255, 50)
    BLUE = (50, 50, 255)
    GREY = (200, 200, 200)
    ORANGE = (200, 100, 50)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    TRANS = (1, 1, 1)


class Window:
    """ Main window class """

    def __init__(self, window_width, window_height, window_frame=pygame.NOFRAME,
                 window_caption="VU Meter", bg_color=(0, 0, 0),
                 font=pygame.font.Font('freesansbold.ttf', 12)):
        self.width = window_width
        self.height = window_height
        self.caption = window_caption
        self.bg_color = bg_color
        self.font = font

        self.screen = pygame.display.set_mode((window_width, window_height), window_frame)
        pygame.display.set_caption(window_caption)
        self.screen.fill(self.bg_color)

    @staticmethod
    def update():
        """
            update the pygame window
            :return: None
        """
        pygame.display.update()


class dbWindow:
    """ dB Window class for displaying the dB levels on the VU meter"""

    def __init__(self, window_width, window_height, bg_color=(0, 0, 0),
                 font=pygame.font.Font('freesansbold.ttf', 12)):
        self.width = window_width
        self.height = window_height
        self.bg_color = bg_color
        self.font = font
        self.surf = pygame.Surface((self.width, self.height))
        self.updating = False
        self.metering = {'green': 30,  # -10
                         'yellow': 36,  # -4
                         'red': 39,  # -1
                        }

    def draw(self, LevelL=0, LevelR=0):
        """
        Draw the db meter
        :param LevelL: Left channel Level
        :param LevelR: Right Channel Level
        :return: Nothing
        """
        self.surf.fill(self.bg_color)

        # Write the scale and draw in the lines
        xpos = 0
        xpos_step_size = 47
        for dB in range(-40, 1, 4):

            # dB numbers on the scale
            # --  0  --
            #    ...
            # -- -20 --
            #    ...
            # -- -40 --
            # draw the numbers
            str_number = str(dB)
            text = self.font.render(str_number, 1, (255, 255, 255))
            text.get_rect()
            self.surf.blit(text, (xpos, 40))

            # draw the lines before and after the numbers
            pygame.draw.line(self.surf, (255, 255, 255), (5 + xpos, 25), (5 + xpos, 35), 1)
            pygame.draw.line(self.surf, (255, 255, 255), (5 + xpos, 55), (5 + xpos, 65), 1)
            xpos += xpos_step_size

        # Draw the meter boxes
        # Green = -40 to -20
        # Yellow = -10 to -5
        # Red = -5 to 0
        # Clipping = +1 +

        # LEFT CHANNEL
        ypos = 10
        for i in range(0, LevelL):
            xpos = (i * 12)-1
            if i < self.metering['green']:
                pygame.draw.rect(self.surf, ColorPicker.GREEN, (xpos, ypos, 30, 12))
            elif self.metering['green'] <= i < self.metering['yellow']:
                pygame.draw.rect(self.surf, ColorPicker.YELLOW, (xpos, ypos, 30, 12))
            elif self.metering['yellow'] <= i < self.metering['red']:
                pygame.draw.rect(self.surf, ColorPicker.RED, (xpos, ypos, 30, 12))
            else:
                pygame.draw.rect(self.surf, ColorPicker.WHITE, (xpos, ypos, 30, 12))

        # RIGHT CHANNEL
        ypos = 69
        for i in range(0, LevelR):
            xpos = (i * 12)-1
            if i < self.metering['green']:
                pygame.draw.rect(self.surf, ColorPicker.GREEN, (xpos, ypos, 30, 12))
            elif self.metering['green'] <= i < self.metering['yellow']:
                pygame.draw.rect(self.surf, ColorPicker.YELLOW, (xpos, ypos, 30, 12))
            elif self.metering['yellow'] <= i < self.metering['red']:
                pygame.draw.rect(self.surf, ColorPicker.RED, (xpos, ypos, 30, 12))
            else:
                pygame.draw.rect(self.surf, ColorPicker.WHITE, (xpos, ypos, 30, 12))

        mainWindow.screen.blit(self.surf, (0, 0))

    def threaded_draw(self, LevelL=0, LevelR=0):
        """
        Draw the window in a separate thread so that the main window is not being locked up
        :param LevelL: Left channel level
        :param LevelR: Right channel level
        :return:
        """
        if not self.updating:
            self.updating = True
            t = threading.Thread(target=self.draw(LevelL=LevelL,
                                                  LevelR=LevelR
                                                 )
                                )
            t.start()


class StatsWindow:
    """ StatsWindow class used for displaying Icecast2 streaming statistics """

    def __init__(self, name, xpos, ypos, window_width, window_height):
        self.name = name
        self.x_position = xpos
        self.y_position = ypos
        self.width = window_width
        self.height = window_height
        self.surf = pygame.surface.Surface((window_width, window_height))  # size of the whole box
        self.font = self.font = pygame.font.SysFont("Verdana", 12)
        self.surf.fill(BGCOLOR)
        self.updating = False

    def draw(self, ics):
        """
        draw the streaming stats window
        :param ics: IcecastServer class
        :return: Nothing
        """
        self.surf_copy = self.surf.copy()

        if not ics.Mounts:
            # no mount points so lets create a NULL mount point
            ics.Mounts.append(NullMountpoint())

        # define text surfaces
        self.title_surf = self.font.render("{}".format(
            ics.Mounts[0].ServerDescription),
                                           True,
                                           ColorPicker.WHITE,
                                           BGCOLOR)

        self.serverStart_surf = self.font.render("Server Start:  {}".format(
            ics.server_start),
                                                 True,
                                                 ColorPicker.WHITE,
                                                 BGCOLOR)

        self.streamStart_surf = self.font.render("Stream Service Start:  {}".format(
            ics.Mounts[0].StreamStart),
                                                 True,
                                                 ColorPicker.WHITE,
                                                 BGCOLOR)

        self.currentListener_surf = self.font.render("Current Listeners:  {}".format(
            ics.listeners),
                                                     True,
                                                     ColorPicker.WHITE,
                                                     BGCOLOR)

        self.peakListener_surf = self.font.render("Peak Listeners:  {}".format(
            ics.Mounts[0].ListenerPeak),
                                                  True,
                                                  ColorPicker.WHITE,
                                                  BGCOLOR)

        self.slowListener_surf = self.font.render("Slow Listeners:  {}".format(
            ics.Mounts[0].SlowListeners),
                                                  True,
                                                  ColorPicker.WHITE,
                                                  BGCOLOR)

        # define text locations and blit
        self._text_display_queue(self.title_surf, xpos=0, ypos=0)
        self._text_display_queue(self.serverStart_surf, xpos=0, ypos=20)
        self._text_display_queue(self.streamStart_surf, xpos=0, ypos=40)
        self._text_display_queue(self.currentListener_surf, xpos=0, ypos=70)
        self._text_display_queue(self.peakListener_surf, xpos=200, ypos=70)
        self._text_display_queue(self.slowListener_surf, xpos=0, ypos=90)

        mainWindow.screen.blit(self.surf_copy, (self.x_position, self.y_position))

        self.updating = False

    def threaded_draw(self, ics):
        """
        Draw the window ina separate thread to prevent locking up the window during the redraw
        :param ics: IcecastServer class
        :return:
        """
        if not self.updating:
            self.updating = True
            t = threading.Thread(target=self.draw(ics))
            t.start()

    def _text_display_queue(self, _surface, xpos, ypos):
        """
        Draw the text surfaces
        :param _surface: text rect
        :param xpos:
        :param ypos:
        :return: None
        """
        _rect = _surface.get_rect(x=xpos, y=ypos)
        self.surf_copy.blit(_surface, _rect)


class VUMeter:
    """ VU Meter class handles the pyaudio input stream as well as analyzing the stream data"""
    FORMAT = pyaudio.paInt16
    pa = pyaudio.PyAudio()
    sound_device_index = 0

    def __init__(self, sample_rate=44100, channels=2, input_channel=1,
                 buffer_size=1024, record_seconds=0.1, input_stream=True):

        for index in range(0, self.pa.get_device_count()):
            sound_device = self.pa.get_device_info_by_index(index)

            if sound_device['name'].find('Loopback: PCM (hw:1,1)') != -1 \
               or sound_device['name'].find('Microphone (Hyper') != -1:
                self.sound_device = sound_device
                self.sound_device_index = index

        if isinstance(sample_rate, int):
            self.sample_rate = sample_rate
        elif isinstance(sample_rate, str):
            if sample_rate.lower() == 'default':
                self.sample_rate = int(self.sound_device['defaultSampleRate'])
            else:
                raise TypeError("Invalid Type for 'sample_rate', expecting 'int'")

        self.peak_left = 0
        self.peak_right = 0
        self.channels = channels
        self.input_channel = input_channel
        self.buffer_size = buffer_size
        self.record_seconds = record_seconds
        self.input_stream = input_stream
        self.stream = None

    def open_stream(self):
        self.stream = self.pa.open(format=self.FORMAT,
                                   channels=self.channels,
                                   rate=self.sample_rate,
                                   input=self.input_stream,
                                   frames_per_buffer=self.buffer_size,
                                   input_device_index=self.sound_device_index)

    def read_stream(self):
        data = array.array('h')
        for i in range(0, int(self.sample_rate / self.buffer_size * self.record_seconds)):
            data.fromstring(self.stream.read(self.buffer_size, exception_on_overflow=False))

        self._get_current_levels(data)

    def _get_current_levels(self, data):

        left_data = audioop.tomono(data, 2, 1, 0)
        amplitude_left = ((audioop.max(left_data, 2)) / 32767)
        self.level_left = (int(41 + (20 * (math.log10(amplitude_left + (1e-40))))))

        right_data = audioop.tomono(data, 2, 0, 1)
        amplitude_right = ((audioop.max(right_data, 2)) / 32767)
        self.level_right = (int(41 + (20 * (math.log10(amplitude_right + (1e-40))))))

        # Use the levels to set the peaks
        if self.level_left > self.peak_left:
            self.peak_left = self.level_left
        elif self.peak_left > 0:
            self.peak_left = self.peak_left - 0.2

        if self.level_right > self.peak_right:
            self.peak_right = self.level_right
        elif self.peak_right > 0:
            self.peak_right = self.peak_right - 0.2


class NullMountpoint:
    """ This is a basic class to provide null values in the event the Icecast mount points
    are not available"""

    def __init__(self):
        self.ServerDescription = "No description available"
        self.StreamStart = "No Stream Start available"
        self.ListenerPeak = "No Listener Peak available"
        self.SlowListeners = "No Slow Listeners available"


class IcecastError(Exception):
    pass


class IcecastInfo:
    """ IcecastInfo uses requests.get to obtan information from the Icecast admin page and
    child mountpoints """

    def __init__(self, name, hostname, port, username, password):
        self.request = requests.Session()
        self.headers = {"User-agent": "Mozilla/5.0"}
        self.http_timeout = 2.0
        self.name = name
        self.hostname = hostname
        self.port = port
        self.username = username
        self._password = password
        self.admin_url = "http://{}:{}/admin/stats.xml".format(self.hostname, self.port)
        self.IceStats = None
        self.Mounts = []
        self.listeners = None
        self.server_start = None
        self.updating = False

    def run(self):
        try:
            req = self.request.get(self.admin_url, auth=(self.username, self._password),
                                   headers=self.headers, timeout=self.http_timeout)
        except ConnectionError as e:
            raise IcecastError(e)
        if req.status_code == 401:
            raise IcecastError("Authentication Failed.")
        elif req.status_code != 200:
            raise IcecastError("Unknown Error.")
        try:
            self.IceStats = ET.fromstring(req.text)
        except:
            raise IcecastError("Error parsing xml.")
        # need to null out the Mounts attribute so that we don't keep growing the list and
        # run the system out of memory
        self.Mounts = []
        self.listeners = self.IceStats.find('listeners').text
        self.server_start = self.IceStats.find('server_start').text

        # Add this server's mounts
        for mount in self.IceStats.iter('source'):
            self.Mounts.append(IcecastMount(mount, self))

        self.updating = False

    def refresh(self):
        if not self.updating:
            # set the flag that the thread is running so that it doesn't run again
            self.updating = True
            threading.Thread(target=self.run(), name='IcecastStats').start()


class IcecastMount:
    """Details pertaining to an Icecast Mount."""

    def __init__(self, mount, server):
        self.IceStats = mount
        self.Listeners = []
        self.Name = self.IceStats.get('mount')

        url = "http://{}:{}/admin/listclients?mount={}".format(
            server.hostname, server.port,
            self.Name)
        try:
            req = requests.get(url, auth=(server.username, server._password),
                               headers=server.headers, timeout=server.http_timeout)
        except ConnectionError as e:
            raise IcecastError(e)

        try:
            self.ListenerStats = ET.fromstring(req.text)
        except:
            raise IcecastError("Invalid Mount XML.")

        # Miscellaneous Information
        try:
            self.ListenerPeak = self.IceStats.find('listener_peak').text
        except AttributeError:
            self.ListenerPeak = None
        try:
            self.ServerDescription = self.IceStats.find('server_description').text
        except AttributeError:
            self.ServerDescription = None
        try:
            self.SlowListeners = self.IceStats.find('slow_listeners').text
        except AttributeError:
            self.SlowListeners = None
        try:
            self.StreamStart = self.IceStats.find('stream_start').text
        except AttributeError:
            self.StreamStart = None

        # Populate the Listeners list for this mount
        for listener in self.ListenerStats.iter('listener'):
            self.Listeners.append(IcecastListener(listener))


class IcecastListener:
    """An Icecast listener."""

    def __init__(self, listener):
        self.IcecastID = listener.get('id')
        self.IP = listener.findtext('IP')
        self.UserAgent = listener.findtext('UserAgent')
        self.Connected = listener.findtext('Connected')
        self.IceStats = listener


def main():
    # create the main VUMeter object to be used
    vu_meter = VUMeter(sample_rate=44100,
                       channels=1,
                       buffer_size=4096,
                       record_seconds=0.2,
                       input_stream=True)
    vu_meter.open_stream()  # Open the stream to start reading from it

    # Define the icecast arguments to be passed to the IcecastInfo class
    # ToDo: read these values from a config file on the system instead of hardcoded
    icecast_args = ("localhost", "127.0.0.1", "8000", "admin", "[redacted]")
    icecast_serv = IcecastInfo(*icecast_args)

    # create the various windows
    fontSmall = pygame.font.Font('freesansbold.ttf', 12)
    mainWindow = Window(WINDOWWIDTH, WINDOWHEIGHT, pygame.NOFRAME,
                        font=fontSmall,
                        bg_color=ColorPicker.BLACK)
    db_Window = dbWindow(WINDOWWIDTH, 200, pygame.NOFRAME,
                         font=fontSmall,
                         bg_color=ColorPicker.BLACK)
    stats_Window = StatsWindow(name="Stats",
                               xpos=5,
                               ypos=100,
                               window_width=WINDOWWIDTH-5,
                               window_height=240)

    # ToDo: read these values from a config file on the system instead of hardcoded
    station_kwargs = {'name': 'KGRO Broadcast',
                      'uri': 'http://localhost:8000/kgro'
                     }
    # ToDo: read these values from a config file on the system instead of hardcoded
    mplayer_kwargs = {'cache': 320,
                      'optional_args': ['-ao', 'alsa']
                     }
    station = StationInfo(**station_kwargs)
    mplayer = StreamPlayer(station)
    mplayer.play(**mplayer_kwargs)

    while True:  # main application loop

        # Read the data and calcualte the left and right levels
        try:
            try:
                icecast_serv.refresh()
                if not mplayer.is_playing():
                    mplayer.play(**mplayer_kwargs)
            except:
                continue

            vu_meter.read_stream()

            # event handling loop for quit events
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                    pygame.quit()
                    sys.exit()

            db_Window.draw(LevelL=vu_meter.level_left,
                           LevelR=vu_meter.level_right
                          )
            stats_Window.threaded_draw(icecast_serv)
            mainWindow.update()

        except BaseException as e:
            print(e)
            if isinstance(e, SystemExit):
                mplayer.stop()
                break
            # on occasion pyaudio will receieve an input overrun and this requires a new
            # pyaudio.PyAudio() object created
            time.sleep(0.1)
            vu_meter = VUMeter(sample_rate=44100,
                               channels=1,
                               buffer_size=4096,
                               record_seconds=0.2,
                               input_stream=True)
            vu_meter.open_stream()

    # one final stop command to ensure all mplayer processes have been cleaned up
    mplayer.stop()


# GLOBAL CONSTANTS
WINDOWWIDTH = 480
WINDOWHEIGHT = 280
BGCOLOR = ColorPicker.BLACK

if __name__ == '__main__':
    main()