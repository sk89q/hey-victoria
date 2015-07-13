# Hey Victoria
# Copyright (C) 2015 Albert Pham <http://www.sk89q.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import struct
import logging
import time
import threading
import audioop

import pyaudio
import speech_recognition as sr

import socket

from .listener import Listener

logger = logging.getLogger(__name__)


class SpeechSession(object):
    """Holds temporary data needed to recognize speech from a user."""

    def __init__(self, client_id, recognizer, responder):
        self.client_id = client_id
        self.responder = responder
        self.listener = Listener(recognizer, responder)
        self.listener.start()

    def unload(self):
        """Call to destroy session."""
        self.listener.running = False

    def read(self, buf, source_channels):
        source_sample_width = pyaudio.get_sample_size(pyaudio.paInt16) * source_channels
        audio = buf[3:]
        try:
            # sometimes the data received is incomplete so reusing state
            # data from ratecv() sometimes results in errors
            (audio, _) = audioop.ratecv(audio, source_sample_width, source_channels, 48000, self.listener.sample_rate, None)
            audio = audioop.tomono(audio, self.listener.sample_width, 0.5, 0.5)
            self.listener.read(audio)
        except audioop.error, e:
            logger.warn("Error preparing sample", exc_info=True)


class UDPListenServer(threading.Thread):
    """
    Listens to UDP packets sent from the TeamSpeak plugin containing
    voice data and other information.
    """

    def __init__(self, addr, agent):
        super(UDPListenServer, self).__init__()
        self.addr = addr
        self.agent = agent
        self.recognizer = sr.Recognizer()
        self.sessions = {} # indexed by TeamSpeak client ID
        self.lock = threading.RLock()

    def get_speaker(self, client_id):
        """
        Gets the state object for the given client ID to recognize
        speech data.
        """
        with self.lock:
            if not client_id in self.sessions:
                self.sessions[client_id] = SpeechSession(client_id, self.recognizer, self.agent)
            s = self.sessions[client_id]
            s.last_access = time.time()
            return s

    def remove_expired(self):
        """Remove old speaker states."""
        with self.lock:
            for k in self.sessions.keys():
                s = self.sessions[k]
                if time.time() - s.last_access > 5:
                    s.unload()
                    del self.sessions[k]

    def listen(self):
        """Listen forever on the given address."""
        self.start()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.addr)

        logger.info("Listening on {}".format(self.addr))

        while True:
            buf, addr = sock.recvfrom(1024 * 8)
            (client_id, source_channels) = struct.unpack("=hB", buf[:3])
            self.get_speaker(client_id).read(buf, source_channels)

    def run(self):
        while True:
            self.remove_expired()
            time.sleep(3)
