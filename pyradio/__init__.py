import subprocess
import psutil
import time
import os


class StationInfo:
    """
    Station Information
    """
    def __init__(self, name, uri):
        self.name = name
        self.stream_uri = uri

    def get_station(self):
        return "{} : {}".format(self.name, self.stream_uri)


class StreamPlayer:
    """
    The radio stream player
    """
    def __init__(self, station_info):
        self.station = station_info
        self._is_running = False
        self.process = None
        self.pids = []
        self.pre_play_pids = []

    def play(self, cache=4096, optional_args=[]):

        cli_args = ['mpg321']
        cli_args = cli_args + optional_args
        cli_args += ['-a', 'hw:1,1']
        if cache < 32:  # mplayer requires cache>=32
            cache = 32

        # cli_args += ['-cache', str(cache)]
        cli_args.append(self.station.stream_uri)

        if self.pids:
            # kill all mplayer processes that were created by this instance if they exist
            for pid in self.pids:
                try:
                    os.kill(pid, 15)
                except:
                    continue
            self.pids = []
            time.sleep(1)  # give it time to clear the processes

        # mplayer seems to open 2 processes but subprocess only knows about 1 process. we need to track any PID changes
        #  for mplayer as the delta is the actual process that are being opened by subprocess.
        self.pre_play_pids = [proc.pid for proc in psutil.process_iter() if proc.name() == 'mpg321']
        self.process = subprocess.Popen(cli_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._is_running = self.is_playing()
        time.sleep(2)  # need to sleep for a couple of seconds as it take mplayer 1-2 seconds to spin up the 2nd process
        self.pids = [proc.pid for proc in psutil.process_iter() if proc.name() == 'mpg321' and
                     not self.pre_play_pids.__contains__(proc.pid)]

    def stop(self):
        # subprocess.kill() will kill the process that subprocess is aware of, however, mplayer opens 2 processes
        # so we need to kill all mplayer processes that were opened prior to logging pre_play_pids
        for pid in self.pids:
            os.kill(pid, 15)  # SIGTERM = 16
        self._is_running = self.is_playing()

    def is_playing(self):
        # If the subprocess.Popen.poll() returns a value then the process is still running
        if self.process.poll():
            self._is_running = False
        else:  # if the subprocess.Popen.poll() returns None then the process is still running
            self._is_running = True

        return self._is_running

