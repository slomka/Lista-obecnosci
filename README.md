# Dziennik zajęć — wersja mobilna (Kivy + Firebase)

To jest **szkielet** prawdziwej aplikacji mobilnej, nie gotowy produkt.
Obejmuje: logowanie, sezony (wrzesień–czerwiec), klasy z możliwością
przepisania na kolejny sezon, globalną listę uczniów przypisywanych do
klas i zaznaczanie obecności ptaszkami — wszystko zsynchronizowane w
chmurze przez Firebase, więc każdy nauczyciel widzi te same dane.

**Czego tu jeszcze nie ma** (naturalny następny krok): historia
frekwencji pogrupowana po miesiącach, drukowanie miesiąca/roku,
zarządzanie kontami nauczycieli z poziomu aplikacji (na razie nowe
konto zakłada się przyciskiem "Załóż nowe konto", a rolę administratora
trzeba nadać ręcznie — patrz krok 4 poniżej).

## 1. Załóż darmowy projekt Firebase

1. Wejdź na https://console.firebase.google.com i utwórz nowy projekt (za darmo).
2. W menu bocznym: **Build → Authentication → Get started** → włącz metodę logowania **E-mail/hasło**.
3. W menu bocznym: **Build → Realtime Database → Create database** → wybierz lokalizację, tryb "zablokowany" (rules zaraz podmienimy).
4. W zakładce **Rules** wklej zawartość pliku `database.rules.json` z tego folderu i opublikuj.

   ⚠️ Te reguły pozwalają **każdemu zalogowanemu** kontu odczytywać i
   zapisywać większość danych — to celowe uproszczenie na start dla
   małego, zaufanego grona nauczycieli. Pełne rozdzielenie uprawnień
   administrator/nauczyciel na poziomie bazy wymaga tzw. custom claims
   i funkcji serwerowej (Cloud Functions), co wykracza poza prosty
   klient mobilny — do rozważenia w kolejnym etapie.

5. W **Ustawieniach projektu** (ikona koła zębatego) znajdź:
   - **Web API Key** → wklej do `firebase_client.py` jako `FIREBASE_API_KEY`
   - Adres Realtime Database (z zakładki Realtime Database, u góry, coś
     w stylu `https://twoj-projekt-default-rtdb.europe-west1.firebasedatabase.app`)
     → wklej jako `FIREBASE_DB_URL`

## 2. Utwórz pierwsze konto administratora

1. Uruchom aplikację na komputerze (patrz krok 3) albo poczekaj do
   pierwszego uruchomienia na telefonie i kliknij **"Załóż nowe konto"**
   swoim adresem e-mail i hasłem.
2. Wejdź do konsoli Firebase → **Realtime Database → Data** → znajdź
   `profiles/<Twoje-UID>` (UID zobaczysz też w Authentication → Users)
   → ręcznie zmień pole `role` z `teacher` na `admin`.
3. Wyloguj się i zaloguj ponownie w aplikacji — powinieneś zobaczyć
   zakładki "Klasy" i "Sezony".

Kolejnych nauczycieli może dodawać każdy przez "Załóż nowe konto" —
domyślnie dostają rolę `teacher`.

## 3. Testowanie na komputerze (najszybszy sposób sprawdzenia logiki)

Kivy działa też jako zwykła aplikacja desktopowa — dobry sposób, żeby
przetestować logikę zanim zbuduje się APK:

```bash
pip install kivy requests
python main.py
```

## 4. Budowa pliku APK (instalacja bez Google Play)

Zbudowanie APK wymaga Android SDK/NDK i działa tylko na Linuksie (lub
w kontenerze/maszynie wirtualnej z Linuksem) — **nie da się tego zrobić
lokalnie na Windows/macOS bez WSL/VM**. Dwie realne opcje:

### Opcja A — GitHub Actions (nie wymaga własnego Linuksa)

1. Wrzuć ten folder do repozytorium na GitHubie.
2. Dodaj plik `.github/workflows/build.yml` wykorzystujący gotową akcję
   `ArtemSBulgakov/buildozer-action` (wyszukaj ją na GitHub Marketplace
   — jest darmowa dla publicznych repozytoriów) skonfigurowaną do
   uruchomienia `buildozer android debug`.
3. Po zakończeniu joba pobierz gotowy plik `.apk` z artefaktów builda.

### Opcja B — własny Linux / maszyna wirtualna

```bash
pip install buildozer cython
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config
buildozer android debug
```
Pierwsza budowa pobiera Android SDK/NDK (kilka GB, wymaga internetu i
zajmuje sporo czasu). Gotowy plik pojawi się w `bin/*.apk`.

## 5. Instalacja na telefonie (bez Google Play)

1. Prześlij plik `.apk` na telefon (e-mail, dysk w chmurze, kabel USB).
2. Na telefonie: **Ustawienia → Bezpieczeństwo → zezwól na instalację z
   nieznanych źródeł** dla aplikacji, przez którą otwierasz plik.
3. Otwórz plik `.apk` i zainstaluj.

Każdy nauczyciel powtarza tylko krok 5 — nie musi nic konfigurować w
Firebase, korzysta z tego samego, jednego projektu, który Ty założyłeś.

## Co dalej

- Historia i drukowanie miesiąca/roku — można dodać analogicznie do
  wersji przeglądarkowej, tylko eksport do PDF na Androidzie wymaga
  dodatkowej biblioteki (np. `reportlab`) zamiast `window.print()`.
- Zarządzanie kontami z poziomu appki (dziś trzeba ręcznie w konsoli
  Firebase) — wymagałoby funkcji serwerowej, bo klient mobilny nie
  powinien mieć uprawnień do zmiany ról innych kont.
- Ikona aplikacji, ekran startowy, tłumaczenie tekstów błędów Firebase.
