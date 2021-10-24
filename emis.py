"""Module for scraping emission sources from the Czech Hydrometeorological Institute.
http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html
"""

import csv
from dataclasses import dataclass, asdict, field, fields
import sys
from typing import List, Tuple

from bs4 import BeautifulSoup
import click
import requests


BASE_URL = 'http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/'
START_URL = (
    'http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html'
)
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:83.0) Gecko/20100101 Firefox/83.0'
}


@dataclass
class Zdroj:
    """Represents emissions source, i.e. one facility."""

    id: int
    nazev: str = field(default=None)
    nace: str = field(default=None)
    ulice_cp: str = field(default=None)
    psc_obec: str = field(default=None)
    souradnice: str = field(default=None)
    adm: str = field(default=None)
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
        filename_sources: str = 'zdroje.csv',
        filename_emissions: str = 'emise.csv',
    ):
        with open(filename_sources, mode='w', newline='') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=Zdroj.get_fieldnames())
            writer.writeheader()
            for row in self.zdroje:
                writer.writerow(asdict(row))
        print(f'Saved {len(self.zdroje)} sources to {filename_sources}.')

        with open(filename_emissions, mode='w', newline='') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=Emise.get_fieldnames())
            writer.writeheader()
            for row in self.emise:
                writer.writerow(asdict(row))
        print(f'Saved {len(self.emise)} emissions to {filename_emissions}.')


def get_bs(url: str) -> BeautifulSoup:
    """Request page and make a soup."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=7)
        r.encoding = 'utf-8'
        bs = BeautifulSoup(r.text, 'html.parser')
        return bs
    except requests.exceptions.ConnectionError:
        print(f'Cannot reach {url}')
        print('Moving on...')
        return None


def get_links(bs: BeautifulSoup) -> List[str]:
    """Return list of links found on the page."""
    links = bs.find('table', {'class': 'data_table'}).find_all('a')
    links = [link.attrs['href'] for link in links]
    return links


def gather_utilities_urls(base_url: str, index_url: str) -> List[str]:
    """Return url of each utility (emission source) as a list."""
    kraje_links = get_links(get_bs(index_url))
    okresy_links = []
    links = []
    # Praha is without okres level
    okresy_links.append(kraje_links[0])
    for kraj_link in kraje_links[1:]:
        okresy_links.extend(get_links(get_bs(base_url + kraj_link)))
    for okres_link in okresy_links:
        links.extend(get_links(get_bs(base_url + okres_link)))
    print(f'Scraped {len(links)} links to emission sources.')
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

    zdroj.nazev = table.find('td', text='Název:').find_next_sibling().get_text()
    zdroj.nace = table.find('td', text='NACE:').find_next_sibling().get_text()
    zdroj.ulice_cp = (
        table.find('td', text='Ulice, č.p./č.o.:').find_next_sibling().get_text()
    )
    zdroj.psc_obec = table.find('td', text='PSČ, Obec:').find_next_sibling().get_text()
    zdroj.souradnice = (
        table.find('td', text='Zeměpisné souřadnice:').find_next_sibling().get_text()
    )
    zdroj.prikon = to_float(
        table.find('td', text='Celkový příkon provozovny [MW]: ')
        .find_next_sibling()
        .get_text()
    )
    try:
        zdroj.adm = (
            table.find('td', text='Adresní místo (ADM):')
            .find_next_sibling()
            .a.get_text()
        )
    except AttributeError:
        pass

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


@click.command()
@click.option(
    '--links/--no-links',
    default=True,
    help='Scrape partial urls to facilities first (default: True)',
)
@click.option(
    '--sources/--no-sources',
    default=False,
    help='Scrape data about emission sources (default: False)',
)
def emis(links, sources):
    """Scrape emission sources from Czech Hydrometeorological Institute."""
    if links:
        urls = gather_utilities_urls(BASE_URL, START_URL)
        with open('linky.txt', 'w') as fin:
            fin.writelines(url + '\n' for url in urls)
        print(f'Loaded {len(urls)} links to emission sources')
    else:
        with open('linky.txt') as fout:
            urls = fout.read().splitlines()

    # Extract data from all urls
    if sources:
        emis_data = Emis()
        with click.progressbar(urls, label='Parsing', show_pos=True) as bar:
            for url in bar:
                bs = get_bs(url)
                if bs:
                    zdroj, emise, paliva = parse_utility(bs, url)
                    emis_data.zdroje.append(zdroj)
                    emis_data.emise.extend(emise)
                    emis_data.paliva.extend(paliva)
        print(f'Parsed {len(emis_data.zdroje)} emission sources')
        emis_data.to_csv()
    else:
        print('Nothing to do. See the options with emis --help')
        sys.exit()


if __name__ == '__main__':
    emis()
