import logging
import pathlib
import sys

import click
import requests
from requests.adapters import HTTPAdapter


from .scrape import get_bs, parse_utility, gather_utilities_urls, Emis, RUIAN_URL


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
@click.option(
    '--ruian/--no-ruian',
    default=False,
    help='Request address and coordinates data from RUIAN API (default: False)',
)
def main(links, sources, ruian):
    """Scrape emission sources from Czech Hydrometeorological Institute."""

    logging.basicConfig(
        filename='emis.log',
        level=logging.INFO,
        format='%(levelname)s %(asctime)s:%(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
    )

    pathlib.Path('data/2020').mkdir(exist_ok=True)

    s = requests.Session()
    s.mount('https://portal.chmi.cz', HTTPAdapter(max_retries=5))

    if links:
        urls = gather_utilities_urls(s)
        with open(pathlib.Path('data/2020/linky.txt'), 'w') as fin:
            fin.writelines(url + '\n' for url in urls)
    else:
        with open(pathlib.Path('data/2020/linky.txt')) as fout:
            urls = fout.read().splitlines()
        logging.info(f'Loaded {len(urls)} links to emission sources')

    # Extract data from all urls
    if sources:
        emis_data = Emis()
        with click.progressbar(urls[:100], label='Parsing sources', show_pos=True) as bar:
            for url in bar:
                bs = get_bs(s, url)
                if bs:
                    zdroj, emise, paliva = parse_utility(bs, url)
                    emis_data.zdroje.append(zdroj)
                    emis_data.emise.extend(emise)
                    emis_data.paliva.extend(paliva)
        logging.info(f'Parsed {len(emis_data.zdroje)} emission sources')
        if ruian:
            ruian_session = requests.Session()
            ruian_session.mount(RUIAN_URL, HTTPAdapter(max_retries=5))
            with click.progressbar(
                emis_data.zdroje, label='Updating geodata from RUIAN', show_pos=True
            ) as bar:
                for zdroj in bar:
                    # If we have Adresní místo, request coordinates and compile address from RUIAN API
                    if zdroj.adm:
                        zdroj.request_address(ruian_session)
                        zdroj.request_coordinates(ruian_session)
                        if zdroj.jtskx and zdroj.jtsky:
                            zdroj.transform_coordinates()  # transform from Krovak to WGS84
            logging.info(f'Updated {len(emis_data.zdroje)} emission sources')
        emis_data.to_csv()
    else:
        logging.info('Nothing to do. See the options with emis --help')
        sys.exit()


main()
