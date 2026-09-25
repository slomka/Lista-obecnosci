"""
Prosty klient REST do Firebase Authentication oraz Realtime Database.
Używa wyłącznie wbudowanej w Pythona biblioteki urllib — żadnych
zewnętrznych zależności, żeby uniknąć problemów z kompatybilnością
skompilowanych pakietów (np. requests/charset_normalizer) na Androidzie.

Wymaga uzupełnienia poniższych stałych danymi z Twojego (darmowego)
projektu Firebase — patrz README.md, sekcja "Konfiguracja Firebase".
"""

import json
import urllib.request
import urllib.error
import urllib.parse

# ---- Projekt: Sportowy Dziennik Zajęć ----
FIREBASE_API_KEY = "AIzaSyCM2FY7muwVIs0uSnNcFgV8apZKxo04VMU"
FIREBASE_DB_URL = "https://sportowy-dziennik-zajec-default-rtdb.firebaseio.com"
# -------------------------------------------

AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


class FirebaseError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _request(method, url, payload=None, timeout=15):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, None
    except urllib.error.URLError as e:
        raise FirebaseError(f"Błąd sieci: {e.reason}")


def _raise_for_auth_error(status, body):
    if status != 200:
        msg = "UNKNOWN_ERROR"
        if body and isinstance(body, dict):
            msg = body.get("error", {}).get("message", "UNKNOWN_ERROR")
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
    url = f"{AUTH_BASE}:signInWithPassword?key={urllib.parse.quote(FIREBASE_API_KEY)}"
    status, body = _request("POST", url, {"email": email, "password": password, "returnSecureToken": True})
    _raise_for_auth_error(status, body)
    return body


def sign_up(email, password):
    """Zakłada nowe konto. Zwraca dict z 'idToken', 'localId' (uid)."""
    url = f"{AUTH_BASE}:signUp?key={urllib.parse.quote(FIREBASE_API_KEY)}"
    status, body = _request("POST", url, {"email": email, "password": password, "returnSecureToken": True})
    _raise_for_auth_error(status, body)
    return body


def db_get(path, id_token):
    """Odczytuje dane spod ścieżki, np. 'classes' albo 'profiles/UID'."""
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={urllib.parse.quote(id_token)}"
    status, body = _request("GET", url)
    if status != 200:
        raise FirebaseError(f"Błąd odczytu ({status})")
    return body


def db_set(path, value, id_token):
    """Nadpisuje dane pod ścieżką (PUT)."""
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={urllib.parse.quote(id_token)}"
    status, body = _request("PUT", url, value)
    if status != 200:
        raise FirebaseError(f"Błąd zapisu ({status})")
    return body


def db_update(path, value, id_token):
    """Aktualizuje częściowo dane pod ścieżką (PATCH), bez nadpisywania reszty."""
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={urllib.parse.quote(id_token)}"
    status, body = _request("PATCH", url, value)
    if status != 200:
        raise FirebaseError(f"Błąd aktualizacji ({status})")
    return body


def db_push(path, value, id_token):
    """Dodaje nowy rekord z automatycznie wygenerowanym kluczem (POST). Zwraca 'name' (nowy klucz)."""
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={urllib.parse.quote(id_token)}"
    status, body = _request("POST", url, value)
    if status != 200:
        raise FirebaseError(f"Błąd zapisu ({status})")
    return body["name"]


def db_delete(path, id_token):
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={urllib.parse.quote(id_token)}"
    status, _ = _request("DELETE", url)
    if status != 200:
        raise FirebaseError(f"Błąd usuwania ({status})")
