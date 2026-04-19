"""
config/territories.py
─────────────────────
Geographic definitions for each sales territory.

Each territory defines:
  - google_maps_locations: list of (lat, lng, radius_meters) tuples for
    Google Maps nearby search. Use overlapping circles to cover the area.
  - search_city_names: city/town names for text-based searches.
  - zip_codes: set of ZIP codes in territory (used for filtering results).

To update: add/remove zip codes or adjust radius circles as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from storage.schema import Territory


@dataclass
class SearchCircle:
    """A lat/lng center point + radius for Google Maps nearby search."""
    lat: float
    lng: float
    radius_meters: int
    label: str  # human-readable label for logging


@dataclass
class TerritoryConfig:
    name: str
    territory: Territory
    search_circles: list[SearchCircle]
    search_city_names: list[str]
    zip_codes: set[str]


# ─────────────────────────────────────────────
# NYC Metro
# ─────────────────────────────────────────────

NYC_METRO = TerritoryConfig(
    name="NYC Metro",
    territory=Territory.NYC_METRO,
    search_circles=[
        SearchCircle(40.7128, -74.0060, 8000,  "Manhattan"),
        SearchCircle(40.6782, -73.9442, 8000,  "Brooklyn"),
        SearchCircle(40.7282, -73.7949, 8000,  "Queens"),
        SearchCircle(40.8448, -73.8648, 8000,  "Bronx"),
        SearchCircle(40.5795, -74.1502, 6000,  "Staten Island"),
        SearchCircle(40.9176, -73.8988, 8000,  "Westchester South"),
        SearchCircle(41.0534, -73.8654, 8000,  "Westchester North"),
    ],
    search_city_names=[
        "Manhattan NY", "Brooklyn NY", "Queens NY", "Bronx NY",
        "Staten Island NY", "Yonkers NY", "White Plains NY",
        "New Rochelle NY", "Mount Vernon NY", "Scarsdale NY",
        "Bronxville NY", "Larchmont NY", "Mamaroneck NY",
    ],
    zip_codes={
        # Manhattan
        "10001","10002","10003","10004","10005","10006","10007","10009",
        "10010","10011","10012","10013","10014","10016","10017","10018",
        "10019","10020","10021","10022","10023","10024","10025","10026",
        "10027","10028","10029","10030","10031","10032","10033","10034",
        "10035","10036","10037","10038","10039","10040","10044","10065",
        "10069","10075","10128","10280","10282",
        # Brooklyn
        "11201","11202","11203","11204","11205","11206","11207","11208",
        "11209","11210","11211","11212","11213","11214","11215","11216",
        "11217","11218","11219","11220","11221","11222","11223","11224",
        "11225","11226","11228","11229","11230","11231","11232","11233",
        "11234","11235","11236","11237","11238","11239",
        # Queens
        "11001","11004","11005","11101","11102","11103","11104","11105",
        "11106","11354","11355","11356","11357","11358","11359","11360",
        "11361","11362","11363","11364","11365","11366","11367","11368",
        "11369","11370","11371","11372","11373","11374","11375","11377",
        "11378","11379","11385","11411","11412","11413","11414","11415",
        "11416","11417","11418","11419","11420","11421","11422","11423",
        "11426","11427","11428","11429","11430","11432","11433","11434",
        "11435","11436",
        # Bronx
        "10451","10452","10453","10454","10455","10456","10457","10458",
        "10459","10460","10461","10462","10463","10464","10465","10466",
        "10467","10468","10469","10470","10471","10472","10473","10474",
        "10475",
        # Staten Island
        "10301","10302","10303","10304","10305","10306","10307","10308",
        "10309","10310","10311","10312","10314",
        # Westchester (key zips)
        "10701","10703","10705","10801","10804","10901","10952",
        "10583","10530","10543","10538","10580","10707","10708",
    },
)


# ─────────────────────────────────────────────
# Long Island (Nassau + Suffolk)
# ─────────────────────────────────────────────

LONG_ISLAND = TerritoryConfig(
    name="Long Island",
    territory=Territory.LONG_ISLAND,
    search_circles=[
        # Nassau County
        SearchCircle(40.7282, -73.6287, 10000, "Nassau West (Great Neck area)"),
        SearchCircle(40.6501, -73.5776, 10000, "Nassau Central (Garden City)"),
        SearchCircle(40.6626, -73.4943, 10000, "Nassau East (Hempstead)"),
        # Suffolk County
        SearchCircle(40.8176, -73.4024, 10000, "Suffolk West (Huntington)"),
        SearchCircle(40.7559, -73.3162, 12000, "Suffolk Central (Smithtown)"),
        SearchCircle(40.9176, -72.8886, 12000, "Suffolk North Fork"),
        SearchCircle(40.7282, -72.6026, 15000, "Suffolk East"),
    ],
    search_city_names=[
        # Nassau
        "Great Neck NY", "Manhasset NY", "Port Washington NY",
        "Garden City NY", "Mineola NY", "Hempstead NY",
        "Rockville Centre NY", "Valley Stream NY", "Lynbrook NY",
        "Hewlett NY", "Woodmere NY", "Lawrence NY",
        "Oceanside NY", "Baldwin NY", "Merrick NY",
        "Bellmore NY", "Wantagh NY", "Seaford NY",
        "Massapequa NY", "Hicksville NY", "Syosset NY",
        "Jericho NY", "Plainview NY", "Bethpage NY",
        "Westbury NY", "Carle Place NY",
        # Suffolk
        "Huntington NY", "Northport NY", "Cold Spring Harbor NY",
        "Commack NY", "Smithtown NY", "Hauppauge NY",
        "Ronkonkoma NY", "Centereach NY", "Stony Brook NY",
        "Port Jefferson NY", "Setauket NY", "Patchogue NY",
        "Babylon NY", "Bay Shore NY", "Islip NY",
        "Amityville NY", "Copiague NY", "Lindenhurst NY",
        "Farmingdale NY", "Brentwood NY",
    ],
    zip_codes={
        # Nassau
        "11020","11021","11022","11023","11024","11025","11030","11040",
        "11041","11042","11043","11044","11050","11051","11052","11053",
        "11054","11055","11096","11501","11507","11509","11510","11514",
        "11516","11518","11520","11530","11531","11542","11545","11547",
        "11548","11549","11550","11551","11552","11553","11554","11555",
        "11556","11557","11558","11559","11560","11561","11563","11565",
        "11566","11568","11569","11570","11571","11572","11575","11576",
        "11577","11579","11580","11581","11582","11590","11596","11598",
        "11599","11710","11714","11735","11753","11756","11758","11762",
        "11765","11771","11783","11793","11801","11802","11803","11804",
        # Suffolk (representative sample — expand as needed)
        "11701","11702","11703","11704","11705","11706","11707","11708",
        "11709","11714","11715","11716","11717","11718","11719","11720",
        "11721","11722","11724","11725","11726","11727","11729","11730",
        "11731","11732","11733","11735","11737","11738","11739","11740",
        "11741","11742","11743","11745","11746","11747","11749","11750",
        "11751","11752","11753","11754","11755","11756","11757","11760",
        "11762","11763","11764","11765","11766","11767","11768","11769",
        "11770","11771","11772","11773","11774","11775","11776","11777",
        "11778","11779","11780","11782","11783","11784","11786","11787",
        "11788","11789","11790","11791","11792","11793","11794","11795",
        "11796","11797","11798","11901","11930","11931","11932","11933",
        "11934","11935","11937","11939","11940","11941","11942","11944",
        "11946","11947","11948","11949","11950","11951","11952","11953",
        "11954","11955","11956","11957","11958","11959","11960","11961",
        "11962","11963","11964","11965","11967","11968","11969","11970",
        "11971","11972","11973","11975","11976","11977","11978","11980",
    },
)


# ─────────────────────────────────────────────
# North Jersey
# ─────────────────────────────────────────────

NORTH_JERSEY = TerritoryConfig(
    name="North Jersey",
    territory=Territory.NORTH_JERSEY,
    search_circles=[
        SearchCircle(40.7178, -74.0431, 8000,  "Jersey City / Hoboken"),
        SearchCircle(40.7957, -74.1754, 8000,  "Newark / Essex"),
        SearchCircle(40.9176, -74.1713, 8000,  "Bergen County South"),
        SearchCircle(40.9951, -74.0775, 8000,  "Bergen County North"),
        SearchCircle(40.7654, -74.2004, 8000,  "Union County"),
        SearchCircle(40.8501, -74.3126, 8000,  "Morris County East"),
    ],
    search_city_names=[
        "Jersey City NJ", "Hoboken NJ", "Weehawken NJ",
        "Newark NJ", "Montclair NJ", "Bloomfield NJ",
        "West Orange NJ", "South Orange NJ", "Maplewood NJ",
        "Millburn NJ", "Short Hills NJ", "Summit NJ",
        "Westfield NJ", "Cranford NJ", "Garfield NJ",
        "Hackensack NJ", "Teaneck NJ", "Englewood NJ",
        "Fort Lee NJ", "Ridgewood NJ", "Fair Lawn NJ",
        "Paramus NJ", "Bergen County NJ", "Morristown NJ",
        "Livingston NJ", "Chatham NJ", "Madison NJ",
    ],
    zip_codes={
        # Hudson County
        "07030","07032","07047","07093","07094","07095","07302","07303",
        "07304","07305","07306","07307","07308","07309","07310","07311",
        "07395","07399",
        # Essex County
        "07001","07002","07003","07006","07009","07017","07018","07019",
        "07021","07028","07040","07041","07042","07043","07044","07050",
        "07051","07052","07055","07060","07068","07101","07102","07103",
        "07104","07105","07106","07107","07108","07109","07110","07111",
        "07112","07113","07114","07175","07181","07182","07183","07184",
        "07185","07188","07189","07191","07192","07193","07194","07195",
        "07198","07199",
        # Bergen County
        "07010","07011","07012","07013","07014","07015","07016","07020",
        "07022","07023","07024","07026","07031","07036","07045","07057",
        "07070","07071","07072","07073","07074","07075","07077","07080",
        "07401","07403","07407","07410","07417","07418","07419","07420",
        "07422","07423","07424","07430","07432","07436","07437","07438",
        "07440","07442","07444","07446","07450","07451","07452","07453",
        "07456","07457","07458","07460","07461","07462","07463","07465",
        "07470","07474","07480","07481","07495","07508","07512","07513",
        # Union County
        "07016","07033","07060","07062","07063","07065","07066","07076",
        "07079","07081","07083","07088","07090","07091","07092",
        # Morris County (east)
        "07801","07802","07803","07806","07820","07821","07825","07828",
        "07834","07836","07840","07842","07843","07847","07849","07850",
        "07853","07856","07857","07860","07865","07866","07869","07870",
        "07871","07874","07876","07878","07879","07881","07882","07885",
        "07920","07921","07922","07924","07926","07927","07928","07930",
        "07931","07932","07933","07934","07935","07936","07938","07939",
        "07940","07945","07946","07950","07960","07961","07962","07963",
        "07970","07974","07976","07977","07978","07979","07980","07981",
        "07983","07999",
    },
)


# ─────────────────────────────────────────────
# Registry — access by Territory enum
# ─────────────────────────────────────────────

TERRITORY_CONFIGS: dict[Territory, TerritoryConfig] = {
    Territory.NYC_METRO:    NYC_METRO,
    Territory.LONG_ISLAND:  LONG_ISLAND,
    Territory.NORTH_JERSEY: NORTH_JERSEY,
}


def get_territory_config(territory: Territory) -> TerritoryConfig:
    """Look up a TerritoryConfig by Territory enum value."""
    config = TERRITORY_CONFIGS.get(territory)
    if not config:
        raise ValueError(f"No config found for territory: {territory}")
    return config
