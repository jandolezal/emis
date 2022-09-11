
# Zdroje znečišťování za rok 2020

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/jandolezal/emis/HEAD)

Modul pro získání dat z [webu EMIS](http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html). Jde o údaje o provozovnách a emisích ohlášených v souhrnné provozní evidenci za rok 2020 na webu ČHMÚ.

Zajištění dat ve struktuře jako na webu ve formátu CSV (včetně nevhodného sdružení některých údajů jako je provozovatel - provozovna nebo psč a obec). Data původně obsahovala také zeměpisné souřadnice, které nyní schází.

Údaje o emisích různých látek sjednoceny pouze do osmi kategorií (TZL, SO2, NOx, CO, VOC, NH3, CO2, ostatní).

Autorem dat je [ČHMÚ](http://portal.chmi.cz/files/portal/docs/uoco/web_generator/plants/index_CZ.html) a jsou zveřejněna pod licencí [CC BY-NC-ND 3.0 CZ](https://creativecommons.org/licenses/by-nc-nd/3.0/cz/).

ČHMÚ zveřejňuje také [souhrnné bilance](http://pr-asu.chmi.cz:8080/EmisBilanceView/faces/viewBilance.xhtml) za kraje pro nejdůležitější škodliviny.

## Použití

`python3 -m venv venv`

`pip install .` nebo `python -m emis --help`

`emis --help`

## TODO

Doplnit kolonku Paliva pro technologie a Přehled vyjmenovaných zdrojů.
