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

BIN_DIR = path.abspath("bin")
RESOURCE_DIR = path.abspath(path.join(path.dirname(__file__), "resource"))
DATA_DIR = path.abspath(path.join(path.dirname(__file__), "data"))
PS_MODEL_DIR = "pocketsphinx/model"
PS_DATA_DIR = "pocketsphinx/test/data"
