
# Alternative version 

from emis import get_bs, get_links

def gather_utilities_urls(base_url, index_url):
    """Return url of each utility (provozovna) as a list.
    """
    kraje_links = get_links(get_bs(index_url))
    okresy_links = []
    links = []
    # Praha is without okres level
    okresy_links.append(kraje_links[0])
    for kraj_link in kraje_links[1:]: 
        okresy_links.extend(get_links(get_bs(base_url + kraj_link)))
    for okres_link in okresy_links:
        links.extend(get_links(get_bs(base_url + okres_link)))
    print(f'Z webu EMIS vráceno {len(links)} odkazů na zdroje znečištění')
    assert len(links) == len(set(links)), 'Duplicitní odkazy'
    return links

if __name__ == '__main__':
    base_url = 'http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/'
    index_url = 'http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html'
    links = gather_utilities_urls(base_url, index_url)
