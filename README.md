# Radar Okazji – wyszukiwarka ofert pojazdów

Program okienkowy (Windows) szukający ofert na Otomoto i OLX.

Pola: cel (pojazd), marka, model, rok (od–do), cena (od–do), twoja lokalizacja
(program liczy odległość w linii prostej do każdej oferty), opis (słowa
kluczowe) oraz webhook Discorda (wiadomość ze wzorem tych pól + ping @everyone
dla każdej *nowej* oferty; opcja automatycznego wyszukiwania co N minut).

## Uruchomienie
    cd radar
    pip install -r requirements.txt
    python app.py

## Budowa .exe (na Windows)
Dwuklik na `radar/build.bat` albo `python build_exe.py` → `radar/dist/RadarOkazji.exe`.
Bez Pythona na PC: GitHub → Actions → „Build EXE” → artefakt `RadarOkazji`.

Ustawienia i lista widzianych ofert: `%APPDATA%\RadarOkazji`.
