#!/usr/bin/env python
# coding: utf-8

import csv
from dataclasses import dataclass, asdict, field, fields
import unicodedata

from bs4 import BeautifulSoup
import click
import requests


@dataclass
class Zdroj:

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
        """Aggegate emissions into eight most important groups. Returns a string
        of the emission group (e.g. carbon monoxide, NH3 etc.).
        Labels: 'tzl', 'so2', 'nox', 'co', 'voc', 'amoniak', 'co2', 'ostatni'.
        """
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

    zdroj_id: int
    nazev: str = field(default=None)
    mnozstvi: float = field(default=None)

    @classmethod
    def get_fieldnames(cls) -> list:
        return [field.name for field in fields(cls)]


@dataclass
class PalivoSpalovaci:

    zdroj_id: int
    nazev: str = field(default=None)


@dataclass
class Indexes:

    emise_start: int
    emise_end: int
    paliva_start: int
    paliva_end: int


@dataclass
class Emis:

    zdroje: list = field(default_factory=list)
    emise: list = field(default_factory=list)
    paliva: list = field(default_factory=list)

    def to_csv(self):
        with open('emis_2019_zdroje.csv', mode='w', newline='') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=Zdroj.get_fieldnames())
            writer.writeheader()
            for row in self.zdroje:
                writer.writerow(asdict(row))

        with open('emis_2019_emise.csv', mode='w', newline='') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=Emise.get_fieldnames())
            writer.writeheader()
            for row in self.emise:
                writer.writerow(asdict(row))


def get_bs(url):
    """Return list of all links from a single webpage (table with kraje and okresy
    on EMIS website).
    """
    r = requests.get(url)
    r.encoding = 'utf-8'
    bs = BeautifulSoup(r.text, 'html.parser')
    return bs


def get_links(bs):
    """Return list of links found on the page.
    bs: BeautifulSoup object
    """
    links = bs.find('table', {'class': 'data_table'}).find_all('a')
    links = [link.attrs['href'] for link in links]
    return links


def has_utilities(bs):
    """Return True if bs (BeautifulSoup object) contanins list of utilities."""
    if bs.find('h2', text='Seznam provozoven'):
        return True
    return False


def gather_links(base_url, urls, gathered):
    """Walk through the website and return only links from pages with utilities.
    base_url: domain url (string)
    urls: links to search through (list of strings)
    gathered: links (list of strings)
    """
    for url in urls:
        bs = get_bs(base_url + url)
        links = get_links(bs)
        if has_utilities(bs):
            gathered.extend(links)
        else:
            gather_links(base_url, links, gathered)
    return gathered


def get_indexes(bs):
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


def retrieve_id(url):
    return int(url.split('/')[-1].strip('_CZ.html'))


def to_float(num_as_string):
    try:
        return float(num_as_string.replace(',', '.').replace(' ', ''))
    except ValueError:
        return None


def parse_utility(bs: BeautifulSoup, url: str) -> tuple:
    """Return parsed utility as a tuple of one source, list of emissions and list of fuels."""
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


def prepare_links(base_url, urls):
    links = gather_links(base_url, urls, [])
    with open('emis_2019_links.txt', 'w') as fout:
        fout.writelines(link + '\n' for link in links)

    print(f'Z webu EMIS vráceno {len(links)} odkazů na zdroje znečištění')
    assert len(links) == len(set(links)), 'Duplicitní odkazy v seznamu'

    return links


@click.command()
@click.option(
    '--urls/--no-urls',
    default=True,
    help='Scrape partial urls to facilities first (default: True)',
)
def emis(urls):
    """Scrape emission sources from Czech Hydrometeorological Institute."""
    base_url = 'http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/'
    urls = ['index_CZ.html']

    if urls:
        links = prepare_links(base_url, urls)
    else:
        with open('emis_2019_links.txt') as fout:
            links = fout.read().splitlines()

    # Extract data from all urls
    emis_data = Emis()

    for link in links:
        url = base_url + link
        bs = get_bs(url)
        zdroj, emise, paliva = parse_utility(bs, url)
        emis_data.zdroje.append(zdroj)
        emis_data.emise.extend(emise)
        emis_data.paliva.extend(paliva)

        if links.index(link) % 1000 == 0:
            print(f'Zpracováno {links.index(link)} odkazů z {len(links)}')

    emis_data.to_csv()

    print(
        f'V seznamu je celkem {len(emis_data.zdroje)} provozoven (zdrojů znečištění).'
    )


if __name__ == '__main__':
    emis()
