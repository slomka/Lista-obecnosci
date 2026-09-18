"""
Dziennik zajęć online — wersja mobilna (Kivy).

Ten plik to punkt wyjścia do prawdziwej aplikacji na telefon, nie gotowy,
przetestowany produkt. Obejmuje najważniejszy szkielet: logowanie,
sezony, klasy, globalną listę uczniów z przypisywaniem do klas oraz
zaznaczanie obecności ptaszkami — z danymi wspólnymi w chmurze (Firebase).
Historia i drukowanie z wersji przeglądarkowej NIE są tu jeszcze
zaimplementowane — to naturalny kolejny krok rozbudowy.

Zanim uruchomisz/zbudujesz:
1. Uzupełnij dane swojego projektu Firebase w firebase_client.py.
2. Przeczytaj README.md — tam są kroki budowy APK (Buildozer / GitHub Actions).
"""

import datetime as dt

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.metrics import dp

import firebase_client as fb

MONTHS_PL = ["styczeń","luty","marzec","kwiecień","maj","czerwiec","lipiec",
             "sierpień","wrzesień","październik","listopad","grudzień"]


def today_iso():
    return dt.date.today().isoformat()


def show_message(title, text):
    Popup(title=title, content=Label(text=text), size_hint=(0.8, 0.4)).open()


class AppState:
    """Trzyma dane sesji i buforowane dane z Firebase."""
    def __init__(self):
        self.id_token = None
        self.uid = None
        self.role = None          # "admin" | "teacher"
        self.display_name = ""
        self.profiles = {}        # uid -> {role, displayName, email}
        self.seasons = {}         # id -> {startYear, endYear}
        self.classes = {}         # id -> {name, seasonId, teacherUid, studentIds: {sid: True}}
        self.students = {}        # id -> {name}
        self.current_season_id = None
        self.current_class_id = None
        self.attendance = {}      # date -> {studentId: status}

    def is_admin(self):
        return self.role == "admin"

    def season_label(self, sid):
        s = self.seasons.get(sid)
        return f"{s['startYear']}/{s['endYear']}" if s else "?"

    def visible_class_ids(self):
        ids = [cid for cid, c in self.classes.items() if c.get("seasonId") == self.current_season_id]
        if self.role == "teacher":
            ids = [cid for cid in ids if self.classes[cid].get("teacherUid") == self.uid]
        return ids

    def current_class(self):
        return self.classes.get(self.current_class_id)

    def assigned_student_ids(self):
        c = self.current_class()
        if not c:
            return []
        return list((c.get("studentIds") or {}).keys())


STATE = AppState()


# ---------------------------------------------------------------- LOGIN ----

class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(12))
        root.add_widget(Label(text="Dziennik zajęć online", font_size=dp(22), size_hint_y=None, height=dp(40)))
        root.add_widget(Label(text="Zaloguj się kontem e-mail", size_hint_y=None, height=dp(24)))

        self.email = TextInput(hint_text="E-mail", multiline=False, size_hint_y=None, height=dp(44))
        self.password = TextInput(hint_text="Hasło", multiline=False, password=True, size_hint_y=None, height=dp(44))
        root.add_widget(self.email)
        root.add_widget(self.password)

        self.status = Label(text="", color=(0.7, 0.25, 0.2, 1), size_hint_y=None, height=dp(30))
        root.add_widget(self.status)

        login_btn = Button(text="Zaloguj", size_hint_y=None, height=dp(48))
        login_btn.bind(on_release=lambda *_: self.do_login())
        root.add_widget(login_btn)

        register_btn = Button(text="Załóż nowe konto (nauczyciel)", size_hint_y=None, height=dp(40))
        register_btn.bind(on_release=lambda *_: self.do_register())
        root.add_widget(register_btn)

        note = Label(
            text=("Pierwsze założone konto trzeba ręcznie ustawić jako "
                  "administratora w konsoli Firebase (patrz README)."),
            size_hint_y=None, height=dp(60), font_size=dp(12)
        )
        root.add_widget(note)
        root.add_widget(BoxLayout())  # spacer
        self.add_widget(root)

    def do_login(self):
        email = self.email.text.strip()
        password = self.password.text
        if not email or not password:
            self.status.text = "Podaj e-mail i hasło."
            return
        try:
            result = fb.sign_in(email, password)
        except fb.FirebaseError as e:
            self.status.text = e.message
            return
        self._enter_app(result)

    def do_register(self):
        email = self.email.text.strip()
        password = self.password.text
        if not email or not password:
            self.status.text = "Podaj e-mail i hasło."
            return
        try:
            result = fb.sign_up(email, password)
            fb.db_set(f"profiles/{result['localId']}", {
                "email": email, "role": "teacher", "displayName": email.split("@")[0]
            }, result["idToken"])
        except fb.FirebaseError as e:
            self.status.text = e.message
            return
        self._enter_app(result)

    def _enter_app(self, auth_result):
        STATE.id_token = auth_result["idToken"]
        STATE.uid = auth_result["localId"]
        try:
            profile = fb.db_get(f"profiles/{STATE.uid}", STATE.id_token) or {}
        except fb.FirebaseError as e:
            self.status.text = e.message
            return
        STATE.role = profile.get("role", "teacher")
        STATE.display_name = profile.get("displayName", "")
        self.status.text = ""
        self.manager.get_screen("main").on_enter_app()
        self.manager.current = "main"


# ----------------------------------------------------------------- MAIN ----

class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.root_box = BoxLayout(orientation="vertical")
        self.add_widget(self.root_box)

        # header
        header = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8), spacing=dp(8))
        self.title_label = Label(text="Dziennik zajęć", bold=True)
        logout_btn = Button(text="Wyloguj", size_hint_x=None, width=dp(90))
        logout_btn.bind(on_release=lambda *_: self.logout())
        header.add_widget(self.title_label)
        header.add_widget(logout_btn)
        self.root_box.add_widget(header)

        # season / class switcher
        switcher = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(8), 0), spacing=dp(8))
        self.season_spinner = Spinner(text="Sezon")
        self.season_spinner.bind(text=lambda *_: self.on_season_change())
        self.class_spinner = Spinner(text="Klasa")
        self.class_spinner.bind(text=lambda *_: self.on_class_change())
        switcher.add_widget(self.season_spinner)
        switcher.add_widget(self.class_spinner)
        self.root_box.add_widget(switcher)

        # tab bar
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(2))
        self.root_box.add_widget(self.tab_bar)

        # content area
        self.content = BoxLayout(orientation="vertical")
        self.root_box.add_widget(self.content)

        self.tabs = {}
        self._build_tab_bar()
        self.active_tab = "obecnosc"

    def _build_tab_bar(self):
        self.tab_bar.clear_widgets()
        defs = [("obecnosc", "Obecność"), ("uczniowie", "Uczniowie")]
        if STATE.is_admin():
            defs += [("klasy", "Klasy"), ("sezony", "Sezony")]
        for key, label in defs:
            btn = Button(text=label)
            btn.bind(on_release=lambda inst, k=key: self.switch_tab(k))
            self.tab_bar.add_widget(btn)

    def on_enter_app(self):
        self.title_label.text = f"Dziennik zajęć — {STATE.role}"
        self._build_tab_bar()
        self.reload_all()

    def logout(self):
        STATE.__init__()
        self.manager.current = "login"

    # ---- data loading ----

    def reload_all(self):
        try:
            STATE.seasons = fb.db_get("seasons", STATE.id_token) or {}
            STATE.classes = fb.db_get("classes", STATE.id_token) or {}
            STATE.students = fb.db_get("students", STATE.id_token) or {}
        except fb.FirebaseError as e:
            show_message("Błąd sieci", e.message)
            return
        if not STATE.seasons:
            self.create_next_season()
        if not STATE.current_season_id and STATE.seasons:
            STATE.current_season_id = sorted(STATE.seasons.keys(),
                                              key=lambda k: STATE.seasons[k]["startYear"])[0]
        self._refresh_switchers()
        self.load_attendance()
        self.switch_tab(self.active_tab)

    def load_attendance(self):
        STATE.attendance = {}
        if not STATE.current_class_id:
            return
        try:
            data = fb.db_get(f"attendance/{STATE.current_class_id}", STATE.id_token) or {}
        except fb.FirebaseError:
            data = {}
        STATE.attendance = data

    def _refresh_switchers(self):
        season_ids = sorted(STATE.seasons.keys(), key=lambda k: STATE.seasons[k]["startYear"])
        self.season_spinner.values = [STATE.season_label(sid) for sid in season_ids]
        self._season_id_by_label = {STATE.season_label(sid): sid for sid in season_ids}
        if STATE.current_season_id:
            self.season_spinner.text = STATE.season_label(STATE.current_season_id)

        class_ids = STATE.visible_class_ids()
        self._class_id_by_label = {STATE.classes[cid]["name"]: cid for cid in class_ids}
        self.class_spinner.values = list(self._class_id_by_label.keys())
        if class_ids and STATE.current_class_id not in class_ids:
            STATE.current_class_id = class_ids[0]
        if STATE.current_class_id and STATE.current_class_id in STATE.classes:
            self.class_spinner.text = STATE.classes[STATE.current_class_id]["name"]
        else:
            self.class_spinner.text = "Brak klas"

    def on_season_change(self):
        label = self.season_spinner.text
        sid = getattr(self, "_season_id_by_label", {}).get(label)
        if sid and sid != STATE.current_season_id:
            STATE.current_season_id = sid
            STATE.current_class_id = None
            self._refresh_switchers()
            self.load_attendance()
            self.switch_tab(self.active_tab)

    def on_class_change(self):
        label = self.class_spinner.text
        cid = getattr(self, "_class_id_by_label", {}).get(label)
        if cid and cid != STATE.current_class_id:
            STATE.current_class_id = cid
            self.load_attendance()
            self.switch_tab(self.active_tab)

    def create_next_season(self):
        today = dt.date.today()
        start_year = today.year if today.month >= 9 else (today.year - 1 if today.month <= 6 else today.year)
        existing_years = [s["startYear"] for s in STATE.seasons.values()]
        if existing_years:
            start_year = max(existing_years) + 1
        if start_year in existing_years:
            return
        season = {"startYear": start_year, "endYear": start_year + 1}
        new_id = fb.db_push("seasons", season, STATE.id_token)
        STATE.seasons[new_id] = season
        if not STATE.current_season_id:
            STATE.current_season_id = new_id

    # ---- tabs ----

    def switch_tab(self, key):
        self.active_tab = key
        self.content.clear_widgets()
        if key == "obecnosc":
            self.content.add_widget(self._build_attendance_tab())
        elif key == "uczniowie":
            self.content.add_widget(self._build_students_tab())
        elif key == "klasy":
            self.content.add_widget(self._build_classes_tab())
        elif key == "sezony":
            self.content.add_widget(self._build_seasons_tab())

    # ---- Obecność ----

    def _build_attendance_tab(self):
        box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        cls = STATE.current_class()
        if not cls:
            box.add_widget(Label(text="Wybierz lub utwórz klasę."))
            return box

        date_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self._current_date = getattr(self, "_current_date", today_iso())
        date_label = Label(text=self._current_date)
        prev_btn = Button(text="<", size_hint_x=None, width=dp(44))
        next_btn = Button(text=">", size_hint_x=None, width=dp(44))

        def change_day(delta):
            d = dt.date.fromisoformat(self._current_date) + dt.timedelta(days=delta)
            self._current_date = d.isoformat()
            self.switch_tab("obecnosc")

        prev_btn.bind(on_release=lambda *_: change_day(-1))
        next_btn.bind(on_release=lambda *_: change_day(1))
        date_row.add_widget(prev_btn)
        date_row.add_widget(date_label)
        date_row.add_widget(next_btn)
        box.add_widget(date_row)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))

        roster = STATE.assigned_student_ids()
        day_data = STATE.attendance.get(self._current_date, {}) or {}

        if not roster:
            grid.add_widget(Label(text="Brak przypisanych uczniów.", size_hint_y=None, height=dp(40)))

        for sid in roster:
            name = STATE.students.get(sid, {}).get("name", "?")
            status = day_data.get(sid, "")
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            row.add_widget(Label(text=name))
            glyphs = {"": "☐", "p": "✓ obecny", "l": "~ spóźniony", "a": "✕ nieobecny"}
            check_btn = Button(text=glyphs.get(status, "☐"), size_hint_x=None, width=dp(120))

            def on_check(inst, sid=sid):
                order = ["", "p", "l", "a"]
                cur = day_data.get(sid, "")
                new_status = order[(order.index(cur) + 1) % len(order)]
                day_data[sid] = new_status
                try:
                    fb.db_set(f"attendance/{STATE.current_class_id}/{self._current_date}/{sid}",
                              new_status, STATE.id_token)
                except fb.FirebaseError as e:
                    show_message("Błąd zapisu", e.message)
                    return
                STATE.attendance.setdefault(self._current_date, {})[sid] = new_status
                self.switch_tab("obecnosc")

            check_btn.bind(on_release=on_check)
            row.add_widget(check_btn)
            grid.add_widget(row)

        scroll.add_widget(grid)
        box.add_widget(scroll)
        return box

    # ---- Uczniowie ----

    def _build_students_tab(self):
        box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        cls = STATE.current_class()

        add_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        name_input = TextInput(hint_text="Imię i nazwisko", multiline=False)
        add_btn = Button(text="Dodaj", size_hint_x=None, width=dp(80))

        def add_student(*_):
            name = name_input.text.strip()
            if not name:
                return
            new_id = fb.db_push("students", {"name": name}, STATE.id_token)
            STATE.students[new_id] = {"name": name}
            if cls is not None:
                student_ids = cls.setdefault("studentIds", {})
                student_ids[new_id] = True
                fb.db_set(f"classes/{STATE.current_class_id}/studentIds/{new_id}", True, STATE.id_token)
            self.switch_tab("uczniowie")

        add_btn.bind(on_release=add_student)
        add_row.add_widget(name_input)
        add_row.add_widget(add_btn)
        box.add_widget(add_row)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))

        assigned = set((cls or {}).get("studentIds", {}).keys()) if cls else set()

        for sid, s in STATE.students.items():
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            row.add_widget(Label(text=s.get("name", "?")))
            if cls is not None:
                toggle = Button(text="W klasie" if sid in assigned else "Dodaj do klasy",
                                 size_hint_x=None, width=dp(120))

                def on_toggle(inst, sid=sid):
                    student_ids = cls.setdefault("studentIds", {})
                    if sid in student_ids:
                        del student_ids[sid]
                        fb.db_delete(f"classes/{STATE.current_class_id}/studentIds/{sid}", STATE.id_token)
                    else:
                        student_ids[sid] = True
                        fb.db_set(f"classes/{STATE.current_class_id}/studentIds/{sid}", True, STATE.id_token)
                    self.switch_tab("uczniowie")

                toggle.bind(on_release=on_toggle)
                row.add_widget(toggle)
            grid.add_widget(row)

        scroll.add_widget(grid)
        box.add_widget(scroll)
        return box

    # ---- Klasy (admin) ----

    def _build_classes_tab(self):
        box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        if not STATE.current_season_id:
            box.add_widget(Label(text="Najpierw utwórz sezon."))
            return box

        add_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        name_input = TextInput(hint_text="Nazwa klasy", multiline=False)
        add_btn = Button(text="Dodaj", size_hint_x=None, width=dp(80))

        def add_class(*_):
            name = name_input.text.strip()
            if not name:
                return
            new_class = {"name": name, "seasonId": STATE.current_season_id,
                         "teacherUid": "", "studentIds": {}}
            new_id = fb.db_push("classes", new_class, STATE.id_token)
            STATE.classes[new_id] = new_class
            if not STATE.current_class_id:
                STATE.current_class_id = new_id
            self._refresh_switchers()
            self.switch_tab("klasy")

        add_btn.bind(on_release=add_class)
        add_row.add_widget(name_input)
        add_row.add_widget(add_btn)
        box.add_widget(add_row)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter("height"))

        for cid, c in STATE.classes.items():
            if c.get("seasonId") != STATE.current_season_id:
                continue
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            n_students = len((c.get("studentIds") or {}))
            row.add_widget(Label(text=f"{c['name']} ({n_students} uczniów)"))
            rollover_btn = Button(text="Przepisz →", size_hint_x=None, width=dp(100))

            def on_rollover(inst, cid=cid):
                self.rollover_class(cid)

            rollover_btn.bind(on_release=on_rollover)
            row.add_widget(rollover_btn)

            del_btn = Button(text="×", size_hint_x=None, width=dp(40))

            def on_delete(inst, cid=cid):
                fb.db_delete(f"classes/{cid}", STATE.id_token)
                del STATE.classes[cid]
                if STATE.current_class_id == cid:
                    STATE.current_class_id = None
                self._refresh_switchers()
                self.switch_tab("klasy")

            del_btn.bind(on_release=on_delete)
            row.add_widget(del_btn)
            grid.add_widget(row)

        scroll.add_widget(grid)
        box.add_widget(scroll)
        return box

    def rollover_class(self, class_id):
        cls = STATE.classes.get(class_id)
        if not cls:
            return
        season = STATE.seasons.get(cls["seasonId"])
        if not season:
            return
        target_start = season["startYear"] + 1
        target_id = next((sid for sid, s in STATE.seasons.items() if s["startYear"] == target_start), None)
        if not target_id:
            target_season = {"startYear": target_start, "endYear": target_start + 1}
            target_id = fb.db_push("seasons", target_season, STATE.id_token)
            STATE.seasons[target_id] = target_season
        existing_id = next((cid for cid, c in STATE.classes.items()
                             if c["seasonId"] == target_id and c["name"].lower() == cls["name"].lower()), None)
        if existing_id:
            merged = dict(STATE.classes[existing_id].get("studentIds") or {})
            merged.update(cls.get("studentIds") or {})
            fb.db_set(f"classes/{existing_id}/studentIds", merged, STATE.id_token)
            STATE.classes[existing_id]["studentIds"] = merged
            show_message("Przepisano", f"Zaktualizowano „{cls['name']}” w kolejnym sezonie.")
        else:
            new_class = {"name": cls["name"], "seasonId": target_id,
                         "teacherUid": cls.get("teacherUid", ""),
                         "studentIds": dict(cls.get("studentIds") or {})}
            new_id = fb.db_push("classes", new_class, STATE.id_token)
            STATE.classes[new_id] = new_class
            show_message("Przepisano", f"Przepisano „{cls['name']}” do kolejnego sezonu.")
        self._refresh_switchers()
        self.switch_tab("klasy")

    # ---- Sezony (admin) ----

    def _build_seasons_tab(self):
        box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        info = Label(text="Sezon trwa od 1 września do 30 czerwca.", size_hint_y=None, height=dp(30))
        box.add_widget(info)

        add_btn = Button(text="Utwórz kolejny sezon", size_hint_y=None, height=dp(44))

        def on_add(*_):
            self.create_next_season()
            self._refresh_switchers()
            self.switch_tab("sezony")

        add_btn.bind(on_release=on_add)
        box.add_widget(add_btn)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        for sid in sorted(STATE.seasons.keys(), key=lambda k: -STATE.seasons[k]["startYear"]):
            s = STATE.seasons[sid]
            label = f"{s['startYear']}/{s['endYear']}"
            if sid == STATE.current_season_id:
                label += "  (bieżący)"
            grid.add_widget(Label(text=label, size_hint_y=None, height=dp(32)))
        scroll.add_widget(grid)
        box.add_widget(scroll)
        return box


class DziennikApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        return sm


if __name__ == "__main__":
    DziennikApp().run()
