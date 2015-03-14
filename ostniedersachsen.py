#!python3
import re
from urllib.request import urlopen
from bs4 import BeautifulSoup as parse

from pyopenmensa.feed import LazyBuilder, extractDate, buildLegend


def parse_week(url, canteen, type, allergene={}, zusatzstoffe={}):
    document = parse(urlopen(url).read())
    for day_table in document.find_all('table', 'swbs_speiseplan'):
        caption = day_table.find('th', 'swbs_speiseplan_head').text
        if type not in caption:
            continue
        date = extractDate(caption)
        meals = day_table.find_all('tr')
        pos = 0
        while pos < len(meals):
            meal_tr = meals[pos]
            if not meal_tr.find('td'):  # z.B Headline
                pos += 1
                continue
            tds = meal_tr.find_all('td')
            category = re.sub(r' \(\d\)', '', tds[0].text.strip())
            name = tds[1].text.strip()
            if tds[1].find('a', href='http://www.stw-on.de/mensavital'):
                notes = ['MensaVital']
            else:
                notes = []
            for img in tds[2].find_all('img'):
                title = img['title']
                if ':' in title:
                    kind, value = title.split(':')
                    if kind == 'Allergene':
                        for allergen in value.split(','):
                            notes.append(allergene[allergen.strip()])
                    elif kind == 'Zusatzstoffe':
                        for zusatzstoff in value.split(','):
                            notes.append(zusatzstoffe[zusatzstoff.strip()])
                    else:
                        print('Unknown image type "{}"'.format(kind))
                else:
                    notes.append(title.replace('enthält ', ''))
            prices = {
                'student':  tds[3].text,
                'employee': tds[4].text,
                'other':    tds[5].text
            }
            if pos < len(meals) - 1:
                nextTds = meals[pos+1].find_all('td')
                if nextTds[0].text.strip() == '':
                    pos += 1
                    for img in nextTds[1].find_all('img'):
                        notes.append(img['title'])
            pos += 1
            canteen.addMeal(date, category, name, notes, prices)


def parse_url(url, today=False, canteentype='Mittagsmensa', this_week='', next_week=True, legend_url=None):
    canteen = LazyBuilder()
    canteen.legendKeyFunc = lambda v: v.lower()
    if not legend_url:
        legend_url = url[:url.find('essen/') + 6] + 'lebensmittelkennzeichnung'
    legend_doc = parse(urlopen(legend_url)).find(id='artikel').text
    allergene = buildLegend(
        text=legend_doc.replace('\xa0', '_'),
        regex=r'(?P<name>[A-Z]+)_{2,} enthält (?P<value>\w+( |\t|\w)*)'
    )
    allergene['EI'] = 'Ei'
    zusatzstoffe = buildLegend(
        text=legend_doc.replace('\xa0', '_'),
        regex=r'(?P<name>\d+)_{2,} (enthält )?(?P<value>\w+( |\t|\w)*)'
    )
    parse_week(url + this_week, canteen, canteentype,
               allergene=allergene, zusatzstoffe=zusatzstoffe)
    if not today and next_week is True:
        parse_week(url + '-kommende-woche', canteen, canteentype,
                   allergene=allergene, zusatzstoffe=zusatzstoffe)
    if not today and type(next_week) is str:
        parse_week(url + next_week, canteen, canteentype,
                   allergene=allergene, zusatzstoffe=zusatzstoffe)
    return canteen.toXMLFeed()


def register_canteens(providers):
    def city(name, prefix='menus/mensa-', legend_url=None, next_week=None, **canteens):
        city_definition = {
            'handler': parse_url,
            'prefix': 'http://www.stw-on.de/{}/essen/'.format(name) + prefix,
            'canteens': {k.replace('_', '-'): v for k, v in canteens.items()}
        }
        if legend_url:
            city_definition['options'] = {'legend_url': legend_url}
        if next_week is not None:
            city_definition.setdefault('options', {})
            city_definition['options']['next_week'] = next_week
        providers[name] = city_definition

    city('braunschweig', prefix='menus/',
         mensa1_mittag=('mensa-1', 'Mittagsmensa'),
         mensa1_abend=('mensa-1', 'Abendmensa'),
         mensa360=('360', 'Pizza', '-2', '-nachste-woche'),
         mensa2='mensa-2',
         hbk='mensa-hbk',
         legend_url='http://www.stw-on.de/braunschweig/essen/wissenswertes/lebensmittelkennzeichnung')
    city('clausthal', clausthal='clausthal', next_week='-kommend-woche')
    city('hildesheim', prefix='menus/',
         uni='mensa-uni',
         hohnsen='mensa-hohnsen',
         luebecker_strasse=('luebecker-strasse', 'Mittagsausgabe'))
    city('holzminden', hawk='hawk', next_week=False)
    city('lueneburg', prefix='speiseplaene/',
         campus='mensa-campus',
         rotes_feld='rotes-feld')
    city('suderburg', suderburg='suderburg')
    city('wolfenbuettel', ostfalia='ostfalia')
