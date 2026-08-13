# -*- coding: utf-8 -*-
"""Generuje strona/assets/route-data.js z albania.gpx (linia) + tabeli POI (poniżej).
Uruchamiaj po zmianie śladu:  python3 gen_route.py
"""
import xml.etree.ElementTree as ET, json, math, os

GPX = "/Users/anna.nowak/Downloads/Albania/albania.gpx"
OUT = "/Users/anna.nowak/projects/anks/longinada-albania-2026/strona/assets/route-data.js"
TOL = 0.0006  # ~60 m — upraszczanie linii

def load(gpx):
    r = ET.parse(gpx).getroot(); ns = r.tag.split('}')[0][1:]
    return [(float(p.get('lat')), float(p.get('lon'))) for p in r.iter('{%s}trkpt' % ns)]

def rdp(pts, tol):
    if len(pts) < 3: return pts
    def d(p, a, b):
        (y0,x0),(y1,x1),(y2,x2) = p, a, b
        dy, dx = y2-y1, x2-x1
        if dy == 0 and dx == 0: return math.hypot(y0-y1, x0-x1)
        t = max(0, min(1, ((y0-y1)*dy + (x0-x1)*dx) / (dy*dy + dx*dx)))
        return math.hypot(y0-(y1+t*dy), x0-(x1+t*dx))
    stack, keep = [(0, len(pts)-1)], {0, len(pts)-1}
    while stack:
        i, j = stack.pop()
        if j <= i+1: continue
        k, best = None, tol
        for m in range(i+1, j):
            dd = d(pts[m], pts[i], pts[j])
            if dd > best: best, k = dd, m
        if k:
            keep.add(k); stack += [(i, k), (k, j)]
    return [pts[i] for i in sorted(keep)]

# --- POI: dzień, nazwa, lat, lon, opis ------------------------------------
# Dzień 5 to wypad busem po Kosowie — punkty leżą 14–68 km od śladu rowerowego.
POIS = [
 (1, "Podgorica",              42.4304, 19.2594, "Start i meta pętli. Stolica Czarnogóry, 45 m n.p.m."),
 (1, "Kanion Cijevny",         42.4265, 19.4884, "Wąwóz rzeki Cijevna (alb. Cem) — pierwszy podjazd dnia."),
 (1, "Tamarë",                 42.4732, 19.5726, "Pierwsza wioska w Albanii, dolina Cem. Sklep, jedzenie."),
 (2, "Lepushë",                42.5599, 19.7311, "Przełęcz 1348 m nad wioską — najwyższy punkt dnia."),
 (2, "Vermosh",                42.5850, 19.7500, "Najbardziej północna wioska Albanii, 1049 m."),
 (2, "Gusinje",                42.5620, 19.8320, "Powrót do Czarnogóry. Baza pod dolinę Grbaja i Prokletije."),
 (3, "Plav",                   42.5966, 19.9436, "Jezioro Plavskie. TU ODBIERASZ ZEZWOLENIE na Čakor (policja graniczna, pon.–pt.)."),
 (3, "Przełęcz Čakor",         42.6688, 20.0074, "1840 m — najwyższy punkt trasy i granica CZG/Kosowo. Nie jest oficjalnym przejściem: rower tylko z zezwoleniem."),
 (3, "Kanion Rugova",          42.6976, 20.1545, "22 km wąwozu do Peji, ściany do ~1000 m. Zjazd asfaltem."),
 (4, "Patriarchat w Peć",      42.6611, 20.2657, "Cztery cerkwie z XIII–XIV w., siedziba serbskich patriarchów. UNESCO, ochrona KFOR — paszport na wejściu."),
 (4, "Monaster Visoki Dečani", 42.5463, 20.2653, "1327–1335, największy zespół średniowiecznych fresków Serbii (~1000 przedstawień). UNESCO, 9–17, grupy 6–8 osób."),
 (4, "Gjakova (Djakovica)",    42.3844, 20.4284, "Baza na dzień kosowski. Çarshia e Madhe — bazar ponad 1 km długości, wokół meczetu Hadum (1594)."),
 (5, "Jaskinia Gadime",        42.4781, 21.2075, "BUS. Jaskinia w marmurze, kryształy aragonitu, 12–15 °C. Tylko z przewodnikiem, 3–5 EUR."),
 (5, "Prisztina",              42.6673, 21.1643, "BUS. Biblioteka Narodowa, katedra Matki Teresy, NEWBORN, Heroinat."),
 (5, "Gazimestan",             42.6906, 21.1237, "BUS. Pomnik przy polu Bitwy na Kosowym Polu (1389). Tu Milošević mówił w 1989."),
 (5, "Prizren",                42.2173, 20.7437, "BUS. Liga Prizreńska 1878, twierdza Kalaja, meczet Sinana Paszy, Shadervan."),
 (6, "Morinë",                 42.4096, 20.2620, "Przejście graniczne Kosowo → Albania."),
 (6, "Bajram Curri",           42.3639, 20.0773, "Brama do Tropoji, ojczyzna plemienia Krasniqi."),
 (7, "Dragobi",                42.4253, 19.9991, "Wjazd w dolinę Valbony wzdłuż rzeki."),
 (7, "Valbonë",                42.4473, 19.8864, "Park Narodowy Valbona. Nad doliną Maja e Jezercës — 2694 m, najwyższy szczyt Dynarów."),
 (7, "Qafa e Valbonës",        42.4078, 19.8143, "~1795 m. Dawny szlak mulasi Shala–Nikaj. 6–8 h pieszo, rower się PROWADZI."),
 (7, "Theth",                  42.4007, 19.7678, "Kulla e ngujimit (wieża odosobnienia, 200 lek), kościół z 1892 r., Park Narodowy od 1966."),
 (8, "Wodospad Grunas",        42.3930, 19.7720, "25 m, 30 min płaskim szlakiem wzdłuż rzeki. Przed 9:00 bez tłumów."),
 (8, "Qafa e Thorës",          42.3868, 19.7358, "~1680 m. Asfalt od 2021. Pomniki Ferenca Nopcsy i Edith Durham."),
 (8, "Bogë",                   42.3656, 19.6321, "Zjazd z przełęczy, wioska u wylotu doliny."),
 (9, "Koplik",                 42.2050, 19.4370, "Wjazd na nizinę nad jeziorem Szkoderskim. Zaopatrzenie."),
 (9, "Shkodra",                42.0519, 19.4956, "Najstarsze miasto Albanii, twierdza Rozafa, 15 m n.p.m."),
 (10, "Jezioro Szkoderskie",   42.1649, 19.2041, "Wariant jeziorem: droga nad wodą przez Murići i Seoca, falująca."),
 (10, "Virpazar",              42.2450, 19.0930, "Baza nad jeziorem, most i winnice."),
 (10, "Rijeka Crnojevića",     42.3350, 19.0480, "Meander rzeki i stary kamienny most — ostatni punkt przed Podgoricą."),
]

pts = load(GPX)
line = rdp(pts, TOL)
pois = [{"day": d, "name": n, "lat": la, "lon": lo, "blurb": b,
         "url": "dzien-%d.html" % d} for d, n, la, lo, b in POIS]
js = ("// Trasa i punkty — generowane z albania.gpx skryptem gen_route.py.\n"
      "// Linia: %d punktów (uproszczone z %d). Punkty: %d.\n" % (len(line), len(pts), len(pois))
      + "window.TRIP = " + json.dumps({"route": [[round(a,5), round(b,5)] for a,b in line],
                                       "pois": pois}, ensure_ascii=False, indent=1) + ";\n")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(js)
print("zapisane: %s  (linia %d pkt, POI %d, %.0f kB)" % (OUT, len(line), len(pois), len(js)/1024))
