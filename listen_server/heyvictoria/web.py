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

from os import path
import subprocess
import logging

# noinspection PyUnresolvedReferences
from apiclient.discovery import build

from . import BIN_DIR

logger = logging.getLogger(__name__)


class YouTube(object):
    """Accesses information from YouTube."""

    api_service_name = "youtube"
    api_version = "v3"

    def __init__(self, api_key):
        self.youtube = build(self.api_service_name, self.api_version, developerKey=api_key)

    def search(self, query):
        """
        Search YouTube for a video matching the given query, returning
        a tuple of video ID and title if a video is found, otherwise
        None will be returned.
        """

        search_response = self.youtube.search().list(
            q=query,
            part="id,snippet",
            type="video",
            maxResults=1
        ).execute()

        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                id = search_result["id"]["videoId"]
                title = search_result["snippet"]["title"]
                return id, title

    def get_stream_url(self, id):
        """Attempt to get a URL that can be used to play a YouTube video."""
        try:
            return subprocess.check_output(
                [path.join(BIN_DIR, "youtube-dl.exe"), "-g", "-f",
                 "aac/ogg/mp3/webm", "http://youtube.com/watch?v=" + id]).strip()
        except subprocess.CalledProcessError, e:
            raise IOError("Failed to fetch play URL")
