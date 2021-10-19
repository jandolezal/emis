#!/usr/bin/env python
# coding: utf-8

import csv
import unicodedata
import requests
from bs4 import BeautifulSoup

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
    links = bs.find('table', {'class':'data_table'}).find_all('a')
    links = [link.attrs['href'] for link in links]
    return links

def has_utilities(bs):
    """Return True if bs (BeautifulSoup object) contanins list of utilities.
    """
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

def choose_emission_label(compound):
    """Aggegate emissions into eight most important groups. Returns a string
    of the emission group (e.g. carbon monoxide, NH3 etc.).
    Labels: 'tzl', 'so2', 'nox', 'co', 'voc', 'amoniak', 'co2', 'ostatni'.
    """
    compound = compound.lower()
    if ('oxidy dusíku' in compound) or ('oxid dusičitý' in compound):
        return 'nox'
    elif 'oxid uhličitý' in compound:
        return 'co2'
    elif 'oxid uhelnatý' in compound:
        return 'co'
    elif 'těkavé organické' in compound:
        return 'voc'
    elif 'tuhé znečišťující' in compound:
        return 'tzl'
    elif 'oxid siřičitý' in compound:
        return 'so2'
    elif 'amoniak' in compound:
        return 'amoniak'
    else:
        return 'ostatni'

def parse_utility(url):
    """Return data about a single utility (provozovna) as a dictionary.
    """
    bs = get_bs(url)
    table = bs.find('table', {'class':'data_table'})
    prov = {}
    prov['url'] = url
    # Basic data (same for each utility) are extracted using the basic dictionary
    basics = {
        'nazev': 'Název:', 'nace': 'NACE:', 'ulice_cp': 'Ulice, č.p./č.o.:',
        'psc_obec': 'PSČ, Obec:', 'souradnice': 'Zeměpisné souřadnice:',
        'adm': 'Adresní místo (ADM):','prikon': 'Celkový příkon provozovny [MW]: ',
        }
    for basic in basics:
        if basic == 'adm':
            try:
                prov[basic] = table.find('td', text=basics[basic]).find_next_sibling().a.get_text()
            except AttributeError:
                prov[basic] = 'n/a'
        else:
            prov[basic] = table.find('td', text=basics[basic]).find_next_sibling().get_text()
    # Emissions (emise) and fuels (paliva) do not have a specified number of rows
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
    # Fuels are just a name without a value
    fuels = []
    for i in range(start_fuels, end_fuels):
        fuels.append(rows[i].td.get_text())
    # Fuels will be stored as a string, fuels separated by comma.
    prov['paliva'] = ', '.join(fuels)
    # Emissions consist of substance name and value 
    for i in range(start_emiss, end_emiss):
        key = rows[i].td.get_text()
        key = choose_emission_label(key)
        try:
            value = rows[i].td.find_next_sibling().get_text()
        except AttributeError:
            break
        prov[key] = value
    return prov

if __name__ == '__main__':
    base_url = 'http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/'
    urls = ['index_CZ.html']
    links = gather_links(base_url, urls, [])
    print(f'Z webu EMIS vráceno {len(links)} odkazů na zdroje znečištění')
    assert len(links) == len(set(links)), 'Duplicitní odkazy v seznamu'

    # Extracting data from all urls
    emis_data = []
    header = []
    # Build header and parse all utilities
    for link in links:
        item = parse_utility(base_url + link)
        emis_data.append(item)
        header.extend([key for key in item.keys() if key not in header])
        if links.index(link) % 1000 == 0:
            print(f'Zpracováno {links.index(link)} odkazů z {len(links)}')
    print(f'V seznamu je celkem {len(emis_data)} provozoven (zdrojů znečištění).')
    
    with open('emis_2019.csv', mode='w') as csvf:
        writer = csv.writer(csvf, delimiter=',')
        writer.writerow(header)
        for util in emis_data:
            row = []
            for col in header:
                try:
                    row.append(util[col])
                except KeyError:
                    row.append('n/a')
            writer.writerow(row)
    print('CSV zapsáno.')
