#!/usr/bin/env python2.7

import logging
import ConfigParser
import argparse
# noinspection PyUnresolvedReferences
import pyaudio # errors happen if pyaudio isn't loaded first

from heyvictoria.agent import Agent, register_default
from heyvictoria.server import UDPListenServer

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='(%(name)s) %(levelname)s: %(message)s')

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', help='path to a config file')
    args = parser.parse_args()

    config = ConfigParser.RawConfigParser()
    config.read(args.config_file)

    host = config.get("server", "host")
    port = config.getint("server", "port")

    agent = Agent()
    register_default(agent, config)
    agent.start()
    agent.say("Hey Victoria is starting")
    agent.key_phrase_found()
    agent.listening_done()
    assistant = UDPListenServer((host, port), agent)
    assistant.listen()
