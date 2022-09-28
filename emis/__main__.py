import logging
import pathlib
import sys

import click
import requests
from requests.adapters import HTTPAdapter


from .scrape import get_bs, parse_utility, gather_utilities_urls, Emis


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
def main(links, sources):
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
        with click.progressbar(urls, label='Parsing', show_pos=True) as bar:
            for url in bar:
                bs = get_bs(s, url)
                if bs:
                    zdroj, emise, paliva = parse_utility(bs, url)
                    emis_data.zdroje.append(zdroj)
                    emis_data.emise.extend(emise)
                    emis_data.paliva.extend(paliva)
        logging.info(f'Parsed {len(emis_data.zdroje)} emission sources')
        emis_data.to_csv()
    else:
        logging.info('Nothing to do. See the options with emis --help')
        sys.exit()


main()
