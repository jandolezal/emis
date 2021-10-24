from bs4 import BeautifulSoup
import pathlib
import pytest

from emis import parse_utility, Zdroj, get_indexes, Indexes, retrieve_id


@pytest.fixture
def melnik_soup():
    with open(pathlib.Path('tests/elektrarna-melnik.html')) as f:
        return BeautifulSoup(f.read(), 'html.parser')


@pytest.fixture
def kutnahora_soup():
    with open(pathlib.Path('tests/ec-kutna-hora.html')) as f:
        return BeautifulSoup(f.read(), 'html.parser')


@pytest.fixture
def zelenarecyklace_soup():
    with open(pathlib.Path('tests/zelena-recyklace.html')) as f:
        return BeautifulSoup(f.read(), 'html.parser')


def test_get_indexes_melnik(melnik_soup):
    assert get_indexes(melnik_soup) == Indexes(9, 24, 27, 32)


def test_get_indexes_kutnahora(kutnahora_soup):
    assert get_indexes(kutnahora_soup) == Indexes(9, 13, 16, 17)


def test_retrieve_id_melnik():
    url = 'https://www.chmi.cz/files/portal/docs/uoco/web_generator/plants/CZ020/643750021_CZ.html'
    assert retrieve_id(url) == 643750021


def test_parse_utility_melnik(melnik_soup):
    url = 'https://www.chmi.cz/files/portal/docs/uoco/web_generator/plants/CZ020/643750021_CZ.html'

    zdroj, emise, paliva = parse_utility(melnik_soup, url)

    assert zdroj.id == 643750021
    assert zdroj.nazev == 'ČEZ, a. s. - Elektrárna Mělník'
    assert zdroj.nace == '351100'
    assert zdroj.ulice_cp == '255'
    assert zdroj.psc_obec == '277 03 Horní Počaply'
    assert zdroj.adm == '26788497'
    assert zdroj.souradnice == '50° 24´ 55.912" sš 14° 25´ 8.207" vd'
    assert zdroj.prikon == 1976.5

    assert zdroj.tzl == 227.555
    assert zdroj.nox == 2911.331
    assert abs(zdroj.ostatni - 226.4296974) < 0.1

    assert zdroj.paliva == (
        'hnědé uhlí prachové;'
        'nafta;'
        'propan, butan a jejich směsi;'
        'topné oleje nízkosirné (obsah síry více než 0,1% a max. do 1 % vč.);'
        'topné oleje vysokosirné (obsah síry více než 1 %)'
    )

    assert len(emise) == 15
    assert len(paliva) == 5

    assert emise[0].zdroj_id == zdroj.id
    assert emise[0].nazev == 'tuhé znečišťující látky'
    assert emise[0].mnozstvi == 227.555

    assert emise[-1].zdroj_id == zdroj.id
    assert emise[-1].nazev == 'plynné sloučeniny chloru vyjádřené jako chlorovodík'
    assert emise[-1].mnozstvi == 6.906727

    assert paliva[0].nazev == 'hnědé uhlí prachové'
    assert paliva[-1].nazev == 'topné oleje vysokosirné (obsah síry více než 1 %)'


def test_parse_utility_kutnahora(kutnahora_soup):
    url = 'https://www.chmi.cz/files/portal/docs/uoco/web_generator/plants/CZ020/677718061_CZ.html'

    zdroj, emise, paliva = parse_utility(kutnahora_soup, url)

    assert zdroj.id == 677718061
    assert zdroj.nazev == 'EC Kutná Hora s.r.o.'
    assert zdroj.nace == '351100'
    assert zdroj.ulice_cp == '197'
    assert zdroj.psc_obec == '284 01 Kutná Hora'
    assert zdroj.prikon == 25.8

    assert zdroj.tzl == 3.952
    assert zdroj.so2 == 22.254
    assert zdroj.nox == 77.038
    assert zdroj.amoniak == 0

    assert zdroj.paliva == 'bylinná biomasa (sláma, apod.)'

    assert len(emise) == 4
    assert len(paliva) == 1

    assert emise[0].zdroj_id == zdroj.id
    assert emise[0].nazev == 'tuhé znečišťující látky'
    assert emise[0].mnozstvi == 3.952

    assert emise[-1].zdroj_id == zdroj.id
    assert emise[-1].nazev == 'oxid uhelnatý'
    assert emise[-1].mnozstvi == 147.691

    assert paliva[0].nazev == 'bylinná biomasa (sláma, apod.)'
    assert paliva[-1].nazev == 'bylinná biomasa (sláma, apod.)'


def test_parse_utility_zelenarecyklace(zelenarecyklace_soup):
    url = 'https://www.chmi.cz/files/portal/docs/uoco/web_generator/plants/CZ020/697620033_CZ.html'

    zdroj, emise, paliva = parse_utility(zelenarecyklace_soup, url)

    assert zdroj.id == 697620033
    assert zdroj.nazev == 'ZELENÁ RECYKLACE s.r.o.'
    assert zdroj.nace == '000000'
    assert zdroj.ulice_cp == 'Pražská 1163'
    assert zdroj.psc_obec == '252 10 Mníšek pod Brdy'
    assert zdroj.prikon == None

    assert zdroj.tzl == 0

    assert emise == []
    assert paliva == []
