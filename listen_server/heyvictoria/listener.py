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

import collections
import logging
from os import path
import time
import Queue
import threading
import audioop

import pyaudio
import speech_recognition as sr
from pocketsphinx.pocketsphinx import *
# noinspection PyUnresolvedReferences
from sphinxbase.sphinxbase import *

from . import PS_MODEL_DIR, DATA_DIR

KEY_PHRASE = "victoria"
ENERGY_THRESHOLD = 300
SILENCE_LENGTH_THRESHOLD = 2
MINIMUM_LISTEN_TIME = 1
LISTEN_TIMEOUT = 5

logger = logging.getLogger(__name__)

class FakeAudioSource(sr.AudioSource):
    """
    Specifies information that is used by the SpeechRecognition library.
    """

    # noinspection PyMissingConstructor
    def __init__(self, sample_width, sample_rate, channels):
        self.SAMPLE_WIDTH = sample_width
        self.CHANNELS = channels
        self.RATE = sample_rate


class Listener(threading.Thread):
    """
    A listener processes incoming audio data and recognizes the spoken
    words, passing the results on to an agent. There is one agent used
    per client.
    """

    confidence_threshold = 0.6

    def __init__(self, recognizer, agent):
        super(Listener, self).__init__()

        self.recognizer = recognizer
        self.agent = agent
        self.queue = Queue.Queue()
        self.running = True

        self.sample_rate = 16000
        self.sample_width = pyaudio.get_sample_size(pyaudio.paInt16) * 1
        self.channels = 1

        config = Decoder.default_config()
        config.set_string('-hmm', path.join(PS_MODEL_DIR, 'en-us/en-us'))
        config.set_string('-lm', path.join(PS_MODEL_DIR, 'en-us/en-us.lm.dmp'))
        config.set_string('-dict', path.join(DATA_DIR, 'pocketsphinx/model/en-us/victoria-en-us.dict'))
        config.set_string('-logfn', 'NUL')
        config.set_string('-keyphrase', KEY_PHRASE)
        config.set_float('-samprate', self.sample_rate)
        config.set_float('-kws_threshold', 1e-40)

        self.decoder = Decoder(config)
        self.decoder.start_utt()

        self.frames = collections.deque()
        self.listening = -1
        self.silence_start = -1
        self.last_logged_hyp = None

    def read(self, buf):
        """Adds the given audio frames to the queue to be processed."""
        self.queue.put(buf)

    def run(self):
        while self.running:
            try:
                buf = self.queue.get(True, 0.2)
                self._process(buf)
            except Queue.Empty, e:
                # don't listen forever; stop after some time even if the user
                # is not done
                if self.listening > 0 and time.time() - self.listening > LISTEN_TIMEOUT:
                    self._recognize()

    def _process(self, buf):
        """Process the given audio buffer."""

        # key phrase already detected
        if self.listening > 0:
            self.frames.append(buf)

            now = time.time()

            # detect silence so we know when to stop listening
            energy = audioop.rms(buf, self.sample_width)
            if energy > ENERGY_THRESHOLD:
                self.silence_start = -1
            else:
                if self.silence_start < 0:
                    self.silence_start = now

            if self.silence_start >= 0 and now - self.silence_start > SILENCE_LENGTH_THRESHOLD and now - self.listening >= MINIMUM_LISTEN_TIME:
                self._recognize()

        # listening for key phrase
        else:
            self.decoder.process_raw(buf, False, False)
            hypothesis = self.decoder.hyp()
            if hypothesis:
                if hypothesis.hypstr != self.last_logged_hyp:
                    logger.debug("Looking for key phrase in: {}".format(hypothesis.hypstr))
                    self.last_logged_hyp = hypothesis.hypstr

                if KEY_PHRASE in hypothesis.hypstr:
                    self.listening = time.time()
                    logger.info("Found key phrase!")
                    self.agent.key_phrase_found()
                    self.decoder.end_utt()
                    self.decoder.start_utt()
                else:
                    # the hypothesis keeps getting bigger and bigger if the key
                    # phrase is never said, so this is a bad hack to fix it
                    # for now
                    if len(hypothesis.hypstr) > 5000:
                        # todo: probably use history and feed it back
                        self.decoder.end_utt()
                        self.decoder.start_utt()

    def _recognize(self):
        """Attempt recognition based on the stored audio frames."""

        logger.info("Phase 2 recording complete; now recognizing...")
        self.agent.listening_done()

        # prepare audio data
        frame_data = b"".join(list(self.frames))
        flac = self.recognizer.samples_to_flac(FakeAudioSource(self.sample_width, self.sample_rate, self.channels), frame_data)
        audio_data = sr.AudioData(self.sample_rate, flac)

        try:
            results = self.recognizer.recognize(audio_data, True)
            for prediction in results:
                if prediction["confidence"] >= self.confidence_threshold:
                    self.agent.interpret(prediction["text"])
        except LookupError, e:
            self.agent.recognition_failed()
            logger.warn("Phase 2 recognition failure", exc_info=True)

        self.reset()

    def reset(self):
        """Set the instance back to the "listening for key phrase" state."""
        self.frames = collections.deque()
        self.listening = -1
        self.silence_start = -1
        self.last_logged_hyp = None
