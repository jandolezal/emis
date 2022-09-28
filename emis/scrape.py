"""Module for scraping emission sources from the Czech Hydrometeorological Institute.
http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html
"""

import csv
from dataclasses import dataclass, asdict, field, fields
import logging
import pathlib
import socket
import sys
from typing import List, Tuple

from bs4 import BeautifulSoup
import click
from pyproj import Transformer
import requests
from requests.adapters import HTTPAdapter


BASE_URL = 'https://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/'
START_URL = (
    'https://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html'
)
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:83.0) Gecko/20100101 Firefox/83.0'
}
RUIAN_URL = 'http://www.vugtk.cz/euradin/ruian/rest.py/'
RUIAN_COMPILE_ADDRESS = RUIAN_URL + 'CompileAddress/json/'
RUIAN_GEOCODE = RUIAN_URL + 'Geocode/json/'


@dataclass
class Zdroj:
    """Represents emissions source, i.e. one facility."""

    id: int
    nazev: str = field(default=None)
    nace: str = field(default=None)
    nuts3: str = field(default=None)
    ulice_cp: str = field(default=None)
    psc_obec: str = field(default=None)
    adm: str = field(default=None)
    ulice: str = field(default=None)
    cp: str = field(default=None)
    orientacni: str = field(default=None)
    cast: str = field(default=None)
    obvod: str = field(default=None)
    obec: str = field(default=None)
    psc: str = field(default=None)
    jtsky: float = field(default=None)
    jtskx: float = field(default=None)
    lat: float = field(default=None)
    lon: float = field(default=None)
    prikon: float = field(default=None)
    nox: float = field(default=0)
    so2: float = field(default=0)
    co: float = field(default=0)
    co2: float = field(default=0)
    tzl: float = field(default=0)
    voc: float = field(default=0)
    amoniak: float = field(default=0)
    ostatni: float = field(default=0)
    paliva: str = field(default=None)

    def aggregate_emissions(self, emissions_list: list) -> None:
        """Aggegate emissions into eight most important groups."""
        for compound in emissions_list:
            if ('oxidy dusíku' in compound.nazev) or (
                'oxid dusičitý' in compound.nazev
            ):
                self.nox = self.nox + compound.mnozstvi
            elif 'oxid uhličitý' in compound.nazev:
                self.co2 = self.co2 + compound.mnozstvi
            elif 'oxid uhelnatý' in compound.nazev:
                self.co = self.co + compound.mnozstvi
            elif 'těkavé organické' in compound.nazev:
                self.voc = self.voc + compound.mnozstvi
            elif 'tuhé znečišťující' in compound.nazev:
                self.tzl = self.tzl + compound.mnozstvi
            elif 'oxid siřičitý' in compound.nazev:
                self.so2 = self.so2 + compound.mnozstvi
            elif 'amoniak' in compound.nazev:
                self.amoniak = self.amoniak + compound.mnozstvi
            else:
                self.ostatni = self.ostatni + compound.mnozstvi

    def request_address(self) -> None:
        resp = requests.get(
            RUIAN_COMPILE_ADDRESS,
            params={'AddressPlaceId': self.adm, 'ExtraInformation': 'standard'},
        )
        if resp.ok:
            try:
                data = resp.json().get('FormattedOutput1')
                if data:
                    self.ulice = data.get('ulice')
                    self.cp = data.get('č.p.')
                    self.orientacni = data.get('orientační_číslo')
                    self.obvod = data.get('číslo_městského_obvodu')
                    self.cast = data.get('část_obce')
                    self.obec = data.get('obec')
                    self.psc = data.get('PSČ')
            except requests.JSONDecodeError as e:
                logging.warning(f'Cannot process address for {self.id} due to: {e}')

    def request_coordinates(self) -> None:
        resp = requests.get(
            RUIAN_GEOCODE,
            params={'AddressPlaceId': self.adm, 'ExtraInformation': 'standard'},
        )
        if resp.ok:
            try:
                records = resp.json().get('records')
                if records:
                    self.jtskx = records[0]['JTSKX']
                    self.jtsky = records[0]['JTSKY']
            except requests.JSONDecodeError as e:
                logging.warning(f'Cannot process coordinates for {self.id} due to: {e}')

    def transform_coordinates(self) -> None:
        '''Transform coordinates from Krovak to WGS84.'''
        transformer = Transformer.from_crs(5513, 4326, always_xy=True)
        self.lon, self.lat = transformer.transform(self.jtskx, self.jtsky)

    @classmethod
    def get_fieldnames(cls) -> list:
        return [field.name for field in fields(cls)]


@dataclass
class Emise:
    """Represents single compound emissions"""

    zdroj_id: int
    nazev: str = field(default=None)
    mnozstvi: float = field(default=None)

    @classmethod
    def get_fieldnames(cls) -> list:
        return [field.name for field in fields(cls)]


@dataclass
class PalivoSpalovaci:
    """Represents fuel."""

    zdroj_id: int
    nazev: str = field(default=None)


@dataclass
class Indexes:
    """Stores start and end indexes of table rows containing emissions and fuels."""

    emise_start: int
    emise_end: int
    paliva_start: int
    paliva_end: int


@dataclass
class Emis:
    """Stores scraped data from the EMIS website."""

    zdroje: list = field(default_factory=list)
    emise: list = field(default_factory=list)
    paliva: list = field(default_factory=list)

    def to_csv(
        self,
        filename_sources: pathlib.Path = pathlib.Path('data/2020/zdroje.csv'),
        filename_emissions: pathlib.Path = pathlib.Path('data/2020/emise.csv'),
    ):
        with open(filename_sources, mode='w', newline='') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=Zdroj.get_fieldnames())
            writer.writeheader()
            for row in self.zdroje:
                writer.writerow(asdict(row))
        logging.info(f'Saved {len(self.zdroje)} sources to {filename_sources}.')

        with open(filename_emissions, mode='w', newline='') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=Emise.get_fieldnames())
            writer.writeheader()
            for row in self.emise:
                writer.writerow(asdict(row))
        logging.info(f'Saved {len(self.emise)} emissions to {filename_emissions}.')


def get_bs(session: requests.Session, url: str) -> BeautifulSoup:
    """Request page and make a soup."""
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        bs = BeautifulSoup(r.text, 'html.parser')
        return bs
    except (requests.exceptions.RequestException, socket.timeout):
        logging.warning(f'Cannot reach {url}')
        return None


def get_links(bs: BeautifulSoup) -> List[str]:
    """Return list of links found on the page."""
    links = bs.find('table', {'class': 'data_table'}).find_all('a')
    links = [link.attrs['href'] for link in links]
    return links


def gather_utilities_urls(
    session: requests.Session, base_url: str = BASE_URL, index_url: str = START_URL
) -> List[str]:
    """Return url of each utility (emission source) as a list."""
    kraje_links = get_links(get_bs(session, index_url))
    okresy_links = []
    links = []
    # Praha is without okres level
    okresy_links.append(kraje_links[0])
    for kraj_link in kraje_links[1:]:
        okresy_links.extend(get_links(get_bs(session, base_url + kraj_link)))
    for okres_link in okresy_links:
        links.extend(get_links(get_bs(session, base_url + okres_link)))
    logging.info(f'Scraped {len(links)} links to emission sources.')
    # Add base url to scraped slugs
    links = [base_url + link for link in links]
    return links


def get_indexes(bs: BeautifulSoup) -> Indexes:
    # Emissions (emise) and fuels (paliva) do not have a specified number of rows
    table = bs.find('table', {'class': 'data_table'})

    rows = table.find_all('tr')
    for i in range(len(rows)):
        if rows[i].th:
            if rows[i].th.get_text() == 'Emise [t]':
                start_emiss = i + 1
            if rows[i].th.get_text() == 'Doplňující údaje':
                end_emiss = i
            if rows[i].th.get_text() == 'Paliva ze spalovacích procesů':
                start_fuels = i + 1
            if rows[i].th.get_text() == 'Paliva pro technologie':
                end_fuels = i

    return Indexes(start_emiss, end_emiss, start_fuels, end_fuels)


def retrieve_id(url: str) -> str:
    """Prepare id from url."""
    return int(url.split('/')[-1].strip('_CZ.html'))


def retrieve_nuts3(url: str) -> str:
    """Prepare nuts3 code from url."""
    return url.split('/')[-2]


def to_float(num_as_string: str) -> float:
    """Make float from string which represents some number.
    >>> to_float('2,99')
    2.99
    >>> to_float('3 523,25')
    3523.25
    """
    try:
        return float(num_as_string.replace(',', '.').replace(' ', ''))
    except ValueError:
        return None


def parse_utility(
    bs: BeautifulSoup, url: str
) -> Tuple[Zdroj, List[Emise], List[PalivoSpalovaci]]:
    """Return parsed utility as a tuple of single source, list of emissions and list of fuels."""
    table = bs.find('table', {'class': 'data_table'})
    rows = table.find_all('tr')

    indexes = get_indexes(bs)

    emise = []
    paliva = []

    zdroj_id = retrieve_id(url)

    zdroj = Zdroj(id=zdroj_id)
    palivo_spal = PalivoSpalovaci(zdroj_id=zdroj_id)

    zdroj.nuts3 = retrieve_nuts3(url)
    zdroj.nazev = table.find('td', string='Název:').find_next_sibling().get_text()
    zdroj.nace = table.find('td', string='NACE:').find_next_sibling().get_text()
    zdroj.ulice_cp = (
        table.find('td', string='Ulice, č.p./č.o.:').find_next_sibling().get_text()
    )
    zdroj.psc_obec = (
        table.find('td', string='PSČ, Obec:').find_next_sibling().get_text()
    )
    zdroj.prikon = to_float(
        table.find('td', string='Celkový příkon provozovny [MW]: ')
        .find_next_sibling()
        .get_text()
    )
    try:
        zdroj.adm = (
            table.find('td', string='Adresní místo (ADM):')
            .find_next_sibling()
            .a.get_text()
        )
    except AttributeError:
        pass

    # If we have Adresní místo, request coordinates and compile address from RUIAN API
    if zdroj.adm:
        zdroj.request_address()

        zdroj.request_coordinates()

        if zdroj.jtskx and zdroj.jtsky:
            zdroj.transform_coordinates()  # transform from Krovak to WGS84

    for i in range(indexes.emise_start, indexes.emise_end):
        try:
            mnozstvi = to_float(rows[i].td.find_next_sibling().get_text())
            emise.append(
                Emise(
                    zdroj_id=zdroj_id,
                    nazev=rows[i].td.get_text(),
                    mnozstvi=mnozstvi,
                )
            )
        except AttributeError:
            break

    for i in range(indexes.paliva_start, indexes.paliva_end):
        paliva.append(PalivoSpalovaci(zdroj_id=zdroj_id, nazev=rows[i].td.get_text()))

    if emise:
        zdroj.aggregate_emissions(emise)

    if paliva:
        zdroj.paliva = ';'.join(palivo.nazev for palivo in paliva)

    return zdroj, emise, paliva
