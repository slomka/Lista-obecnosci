"""
Prosty klient REST do Firebase Authentication oraz Realtime Database.
Nie wymaga oficjalnego SDK Firebase (który jest ciężki na Androidzie) —
korzysta wyłącznie z biblioteki `requests`, co dobrze działa z Buildozerem.

Wymaga uzupełnienia poniższych stałych danymi z Twojego (darmowego)
projektu Firebase — patrz README.md, sekcja "Konfiguracja Firebase".
"""

import requests

# ---- Projekt: Sportowy Dziennik Zajęć ----
FIREBASE_API_KEY = "AIzaSyCM2FY7muwVIs0uSnNcFgV8apZKxo04VMU"
FIREBASE_DB_URL = "https://sportowy-dziennik-zajec-default-rtdb.firebaseio.com"
# -------------------------------------------

AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


class FirebaseError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _raise_for_auth_error(resp):
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", "UNKNOWN_ERROR")
        except Exception:
            msg = "UNKNOWN_ERROR"
        friendly = {
            "EMAIL_NOT_FOUND": "Nie znaleziono konta o tym adresie e-mail.",
            "INVALID_PASSWORD": "Nieprawidłowe hasło.",
            "INVALID_LOGIN_CREDENTIALS": "Nieprawidłowy e-mail lub hasło.",
            "EMAIL_EXISTS": "Konto z tym adresem e-mail już istnieje.",
            "WEAK_PASSWORD": "Hasło musi mieć co najmniej 6 znaków.",
        }.get(msg, msg)
        raise FirebaseError(friendly)


def sign_in(email, password):
    """Loguje użytkownika. Zwraca dict z 'idToken', 'localId' (uid)."""
    resp = requests.post(
        f"{AUTH_BASE}:signInWithPassword",
        params={"key": FIREBASE_API_KEY},
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=15,
    )
    _raise_for_auth_error(resp)
    return resp.json()


def sign_up(email, password):
    """Zakłada nowe konto. Zwraca dict z 'idToken', 'localId' (uid)."""
    resp = requests.post(
        f"{AUTH_BASE}:signUp",
        params={"key": FIREBASE_API_KEY},
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=15,
    )
    _raise_for_auth_error(resp)
    return resp.json()


def db_get(path, id_token):
    """Odczytuje dane spod ścieżki, np. 'classes' albo 'profiles/UID'."""
    resp = requests.get(
        f"{FIREBASE_DB_URL}/{path}.json",
        params={"auth": id_token},
        timeout=15,
    )
    if resp.status_code != 200:
        raise FirebaseError(f"Błąd odczytu ({resp.status_code})")
    return resp.json()


def db_set(path, value, id_token):
    """Nadpisuje dane pod ścieżką (PUT)."""
    resp = requests.put(
        f"{FIREBASE_DB_URL}/{path}.json",
        params={"auth": id_token},
        json=value,
        timeout=15,
    )
    if resp.status_code != 200:
        raise FirebaseError(f"Błąd zapisu ({resp.status_code})")
    return resp.json()


def db_update(path, value, id_token):
    """Aktualizuje częściowo dane pod ścieżką (PATCH), bez nadpisywania reszty."""
    resp = requests.patch(
        f"{FIREBASE_DB_URL}/{path}.json",
        params={"auth": id_token},
        json=value,
        timeout=15,
    )
    if resp.status_code != 200:
        raise FirebaseError(f"Błąd aktualizacji ({resp.status_code})")
    return resp.json()


def db_push(path, value, id_token):
    """Dodaje nowy rekord z automatycznie wygenerowanym kluczem (POST). Zwraca 'name' (nowy klucz)."""
    resp = requests.post(
        f"{FIREBASE_DB_URL}/{path}.json",
        params={"auth": id_token},
        json=value,
        timeout=15,
    )
    if resp.status_code != 200:
        raise FirebaseError(f"Błąd zapisu ({resp.status_code})")
    return resp.json()["name"]


def db_delete(path, id_token):
    resp = requests.delete(
        f"{FIREBASE_DB_URL}/{path}.json",
        params={"auth": id_token},
        timeout=15,
    )
    if resp.status_code != 200:
        raise FirebaseError(f"Błąd usuwania ({resp.status_code})")
