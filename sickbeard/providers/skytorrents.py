# coding=utf-8
#
# This file is part of SickGear.
#
# SickGear is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickGear is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickGear.  If not, see <http://www.gnu.org/licenses/>.

import re
import traceback

from . import generic
from sickbeard import logger
from sickbeard.bs4_parser import BS4Parser
from sickbeard.helpers import tryInt
from lib.unidecode import unidecode


class SkytorrentsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, 'Skytorrents')

        self.url_base = 'https://skytorrents.lol/'

        self.urls = {'config_provider_home_uri': self.url_base,
                     'search': self.url_base + '?category=show&sort=created&query=%s&page=%s'}

        self.minseed, self.minleech = 2 * [None]

    def _search_provider(self, search_params, **kwargs):

        results = []

        items = {'Cache': [], 'Season': [], 'Episode': [], 'Propers': []}

        rc = dict((k, re.compile('(?i)' + v)) for (k, v) in {
            'info': r'(^(info|torrent)/|/[\w+]{40,}\s*$)', 'get': '^magnet:'}.items())

        for mode in search_params.keys():
            for search_string in search_params[mode]:
                search_string = isinstance(search_string, unicode) and unidecode(search_string) or search_string

                if 'Cache' == mode:
                    search_url = self.urls['search'] % tuple(search_string.split(','))
                else:
                    search_url = self.urls['search'] % (search_string.replace('.', ' '), '')
                html = self.get_url(search_url)
                if self.should_skip():
                    return results

                cnt = len(items[mode])
                try:
                    if not html or self._has_no_results(html):
                        raise generic.HaltParseException

                    parse_only = dict(table={'class': (lambda at: at and 'is-striped' in at)})
                    with BS4Parser(html, parse_only=parse_only, preclean=True) as tbl:
                        tbl_rows = [] if not tbl else tbl.find_all('tr')

                        if 2 > len(tbl_rows):
                            raise generic.HaltParseException

                        head = None
                        for tr in tbl_rows[1:]:
                            cells = tr.find_all('td')
                            if 5 > len(cells):
                                continue
                            try:
                                head = head if None is not head else self._header_row(tr)
                                seeders, leechers, size = [tryInt(n, n) for n in [
                                    cells[head[x]].get_text().strip() for x in 'seed', 'leech', 'size']]
                                if self._reject_item(seeders, leechers):
                                    continue

                                info = tr.select_one(
                                    '[alt*="magnet"], [title*="magnet"], [alt*="torrent"], [title*="torrent"]') \
                                    or tr.find('a', href=rc['info'])
                                title = re.sub(r'\s(using|use|magnet|link)', '', (
                                        info.attrs.get('title') or info.attrs.get('alt') or info.get_text())).strip()
                                download_url = self._link(tr.find('a', href=rc['get'])['href'])
                            except (AttributeError, TypeError, ValueError, KeyError):
                                continue

                            if title and download_url:
                                items[mode].append((title, download_url, seeders, self._bytesizer(size)))

                except generic.HaltParseException:
                    pass
                except (BaseException, Exception):
                    logger.log(u'Failed to parse. Traceback: %s' % traceback.format_exc(), logger.ERROR)

                self._log_search(mode, len(items[mode]) - cnt, search_url)

            results = self._sort_seeding(mode, results + items[mode])

        return results

    def _cache_data(self, **kwargs):

        return self._search_provider({'Cache': ['x264,', 'x264,2', 'x264,3', 'x264,4', 'x264,5']})


provider = SkytorrentsProvider()
