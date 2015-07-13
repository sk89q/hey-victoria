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

import logging
from os import path
import Queue
import threading
import subprocess
import random

import pyttsx
from textblob import TextBlob

from . import BIN_DIR, RESOURCE_DIR
from .web import YouTube

logger = logging.getLogger(__name__)


class FFPlayController(object):
    """
    Plays media files using ffplay from ffmpeg, allowing one maximum
    file playing at a time.
    """

    def __init__(self):
        self.proc = None
        self.lock = threading.RLock()

    def stop(self):
        """Stop anything currently playing."""

        with self.lock:
            if self.proc:
                logger.info("Killing ffplay")

                try:
                    self.proc.kill()
                except Exception, e:
                    pass
                self.proc = None

    def play(self, url):
        """Play the given URL."""

        with self.lock:
            self.stop()

            logger.info("Playing {}".format(url))

            args = [path.join(BIN_DIR, "ffplay.exe"), "-nodisp", "-af", "volume=0.25", url]

            try:
                self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.proc.stdin.close()
                self.proc.stdout.close()
                self.proc.stderr.close()
            except Exception, e:
                logger.warning("Failed to start {}".format(" ".join(args)))


class Agent(threading.Thread):
    """Parses text recognized from speech to perform tasks."""

    did_not_understand = [
        "I didn't understand that",
        "Sorry, say again",
        "I didn't get that",
        "Sorry, please try again",
        "Sorry, please repeat that",
        "Can you say that again?",
    ]

    def __init__(self):
        super(Agent, self).__init__()
        self.tts_queue = Queue.Queue()
        self.media_player = FFPlayController()
        self.actions = {}

    def register_action(self, fn, words):
        """Register an action that the bot can perform."""
        for word in words:
            self.actions[word] = fn

    def say(self, text):
        """Say the given text using TTS."""
        self.tts_queue.put(text)

    def play_sound(self, sound):
        """Play the given sound file."""

        # importing winsound early breaks pyaudio for some reason
        import winsound

        def play():
            winsound.PlaySound(sound, winsound.SND_FILENAME)

        t = threading.Thread(target=play)
        t.start()

    def interpret(self, text):
        """Interpret the given text and react accordingly."""

        logger.info("Interpreting: {}".format(text))

        blob = TextBlob(text.lower())
        tags = blob.tags

        for i in xrange(0, len(tags)):
            lemma = tags[i][0].lemma

            if lemma in self.actions:
                fn = self.actions[lemma]
                logger.info("Found {} for {}".format(fn, lemma))
                args = " ".join([str(t[0]) for t in tags[i + 1:]])
                fn(args)
                return

        self.say("I don't know how to " + tags[0][0])

    def recognition_failed(self):
        """Respond after recognition has failed."""
        self.say(random.choice(self.did_not_understand))

    def key_phrase_found(self):
        """Respond after key phrase has been found."""
        self.play_sound(path.join(RESOURCE_DIR, "key_phrase_found.wav"))

    def listening_done(self):
        """Respond after recording has completed."""
        self.play_sound(path.join(RESOURCE_DIR, "listening_done.wav"))

    def run(self):
        engine = pyttsx.init(debug=True)
        while True:
            # todo: handle overflow
            text = self.tts_queue.get(True)
            engine.say(text)
            engine.runAndWait()


def register_default(agent, config):
    youtube = YouTube(config.get("youtube", "apiKey"))

    def say(args):
        agent.say(args)

    def play(args):
        agent.say("Let me search You Tube")
        try:
            entry = youtube.search(args)
            if entry:
                agent.say("Playing " + entry[1])
                url = youtube.get_stream_url(entry[0])
                agent.media_player.play(url)
            else:
                agent.say("Couldn't find a result for " + args)
        except Exception, e:
            logger.warning("Failed to play YouTube", exc_info=True)
            agent.say("Couldn't play due to an internal error")

    def stop(args):
        agent.say("Stopping playback")
        agent.media_player.stop()

    agent.register_action(say, ("say", "speak", "repeat"))
    agent.register_action(play, ("play", "youtube"))
    agent.register_action(stop, ("stop",))

