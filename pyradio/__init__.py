import subprocess
import psutil
import time
import os
from datetime import datetime


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
        self.started = datetime.now()
        self.process = None
        self.pids = []
        self.pre_play_pids = []

    def play(self, cache=4096, optional_args=[]):

        cli_args = ['mplayer']
        cli_args = cli_args + optional_args

        if cache < 32:  # mplayer requires cache>=32
            cache = 32

        cli_args += ['-cache', str(cache)]
        cli_args.append("127.0.0.1")

        if self.pids:
            # kill all mplayer processes that were created by this instance if they exist
            for pid in self.pids:
                try:
                    os.kill(pid, 15)
                except:
                    continue
            self.pids = []
            time.sleep(1)  # give it time to clear the processes

        # mplayer seems to open 2 processes but subprocess only knows about 1 process. we
        # need to track any PID changes for mplayer as the delta is the actual process that are
        # being opened by subprocess.
        self.pre_play_pids = [proc.pid for proc in psutil.process_iter() if proc.name() ==
                              'mplayer']

        self.process = subprocess.Popen(cli_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._is_running = self.is_playing()
        self.started = datetime.now()
        # need to sleep for a couple of seconds as it take mplayer 1-2 seconds
        # to spin up the 2nd process
        time.sleep(2)
        self.pids = [proc.pid for proc in psutil.process_iter() if proc.name() == 'mplayer' and
                     not self.pre_play_pids.__contains__(proc.pid)]

    def stop(self):
        # subprocess.kill() will kill the process that subprocess is aware of, however,
        # mplayer opens 2 processes so we need to kill all mplayer processes that were
        # opened prior to logging pre_play_pids
        pids = [proc.pid for proc in psutil.process_iter() if proc.name() == 'mplayer' and
                not self.pre_play_pids.__contains__(proc.pid)]
        for pid in pids:
            os.kill(pid, 15)  # SIGTERM = 16
        self.pids = []
        self.started = datetime.now()  # reset the time stamp
        self._is_running = False

    def is_playing(self):
        # If the subprocess.Popen.poll() returns a value then the process is not running
        if self.process.poll():
            self._is_running = False
        else:
            # if the subprocess.Popen.poll() returns None then the process is still running

            # Periodically the stream will be cutoff for a brief moment. However, the way mplayer
            # is launched via subprocess causes 2 processes to be opened but subprocess only knows
            # about the 1st pid. Since we track the pids in self.pids then we can see if both pids
            # are still running. if not then kill the remaining pid and set self._is_running=false
            pids = [proc.pid for proc in psutil.process_iter() if proc.name() == 'mplayer' and
                    not self.pre_play_pids.__contains__(proc.pid)]

            # the longer mplayer streams the more CPU resources are used. So every hour
            # (3600 seconds) lets stop mplayer.
            ntime = datetime.now()
            time_delta = ntime - self.started
            if (ntime.minute == 30 and ntime.second == 5) or (ntime.minute == 0 and ntime.second == 5):
                self.stop()
            else:
                self._is_running = True

        return self._is_running

