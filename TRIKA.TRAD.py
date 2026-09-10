from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line
import os
import threading
import sqlite3
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import random
from kivy.core.video import Video
from gemini_ai import demander_a_trika
import re
# ==================== RECONNAISSANCE VOCALE ANDROID ====================

try:
    from android import activity
    from android.permissions import request_permissions, Permission
    from jnius import autoclass

    ANDROID_DISPONIBLE = True

except ImportError:
    ANDROID_DISPONIBLE = False
# ==================== TTS ANDROID ====================
try:
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
    Locale = autoclass("java.util.Locale")

    TTS_DISPONIBLE = True
except Exception:
    TTS_DISPONIBLE = False



Window.clearcolor = (0.96, 0.94, 0.98, 1)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def fichier(nom):
    return os.path.join(BASE_DIR, nom)
LOGO_PATH = fichier("logo.png")
DRAPEAU_PATH = fichier("drapeau.png")
VIDEO_PATH = fichier("presentation.mp4")



# ============================================================
# 🎨 DESIGN TRIKA.TRAD
# ============================================================

VIOLET_TRIKA = (0.32, 0.16, 0.45, 1)
VIOLET_CLAIR = (0.94, 0.90, 0.98, 1)
VIOLET_TRES_CLAIR = (0.97, 0.95, 0.99, 1)
BLANC = (1, 1, 1, 1)
NOIR = (0.12, 0.10, 0.15, 1)


def fond_arrondi(widget, couleur=BLANC, rayon=22):

    with widget.canvas.before:
        Color(*couleur)

        rect = RoundedRectangle(
            pos=widget.pos,
            size=widget.size,
            radius=[dp(rayon)]
        )

    def update(*args):
        rect.pos = widget.pos
        rect.size = widget.size

    widget.bind(
        pos=update,
        size=update
    )

    return rect


def champ_style(widget):

    """
    Style commun à tous les champs TextInput.
    """

    widget.background_normal = ""
    widget.background_active = ""
    widget.background_color = (0, 0, 0, 0)

    widget.foreground_color = NOIR
    widget.cursor_color = VIOLET_TRIKA

    fond_arrondi(
        widget,
        VIOLET_TRES_CLAIR,
        18
    )

    return widget


def bouton_arrondi(
    texte,
    couleur=VIOLET_TRIKA,
    hauteur=52
):

    bouton = Button(
        text=texte,
        font_size=dp(15),
        bold=True,

        size_hint_y=None,
        height=dp(hauteur),

        background_normal="",
        background_down="",
        background_color=(0, 0, 0, 0),

        color=BLANC
    )

    fond_arrondi(
        bouton,
        couleur,
        30
    )

    # --------------------------------------------------------
    # Animation au toucher
    # --------------------------------------------------------

    def appuyer(instance):

        animation = (
            Animation(
                opacity=0.75,
                duration=0.08
            )
            +
            Animation(
                opacity=1,
                duration=0.12
            )
        )

        animation.start(instance)

    bouton.bind(
        on_press=appuyer
    )

    return bouton

# ==================== DICTIONNAIRE TRIKA.TRAD ====================
DB_PATH = fichier("dictionnaire_trika_nouvelle.db")
# ==================== HISTORIQUE ====================

def initialiser_historique():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texte TEXT NOT NULL,
            traduction TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


initialiser_historique()

def enregistrer_historique(texte, traduction, source, destination):

    if not texte.strip() or not traduction.strip():
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO historique
        (texte, traduction, source, destination)
        VALUES (?, ?, ?, ?)
    """, (
        texte,
        traduction,
        source,
        destination
    ))

    # Garder seulement les 20 dernières traductions
    cur.execute("""
        DELETE FROM historique
        WHERE id NOT IN (
            SELECT id
            FROM historique
            ORDER BY id DESC
            LIMIT 20
        )
    """)

    conn.commit()
    conn.close()

def recuperer_historique():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT texte, traduction, source, destination, date FROM historique ORDER BY id DESC LIMIT 20")
    donnees = cur.fetchall()
    conn.close()
    return donnees

def supprimer_historique():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM historique")

    conn.commit()
    conn.close()

def rechercher_dans_dictionnaire(texte, source, destination):
    if not os.path.exists(DB_PATH):
        return None

    texte = texte.strip()

    if not texte:
        return None

    # Français ↔ Lingala avec SQLite
    if {source, destination} == {"🇫🇷 Français", "🇨🇬 Lingala"}:

        colonne_source = "francais" if source == "🇫🇷 Français" else "lingala"
        colonne_destination = "lingala" if source == "🇫🇷 Français" else "francais"

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        try:
            cur.execute(f"SELECT {colonne_destination} FROM dictionnaire WHERE LOWER(TRIM({colonne_source})) = LOWER(TRIM(?)) LIMIT 1", (texte,))
            row = cur.fetchone()

            if row and row[0]:
                return str(row[0])

            mots = re.findall(r"[A-Za-zÀ-ÿ'’-]+|[^A-Za-zÀ-ÿ'’-]+", texte)
            resultat = []
            trouve = 0

            for morceau in mots:

                if not re.fullmatch(r"[A-Za-zÀ-ÿ'’-]+", morceau):
                    resultat.append(morceau)
                    continue

                cur.execute(f"SELECT {colonne_destination} FROM dictionnaire WHERE LOWER(TRIM({colonne_source})) = LOWER(TRIM(?)) LIMIT 1", (morceau,))
                row = cur.fetchone()

                if row and row[0]:
                    resultat.append(str(row[0]))
                    trouve += 1
                else:
                    resultat.append(morceau)

            return "".join(resultat) if trouve else None

        finally:
            conn.close()

    return None

def traduire_anglais(texte, source, destination):
    try:

        if source == "🇫🇷 Français" and destination == "🇬🇧 Anglais":
            return GoogleTranslator(source="fr", target="en").translate(texte)

        if source == "🇬🇧 Anglais" and destination == "🇫🇷 Français":
            return GoogleTranslator(source="en", target="fr").translate(texte)

        if source == "🇨🇬 Lingala" and destination == "🇬🇧 Anglais":
            francais = rechercher_dans_dictionnaire(
                texte,
                "🇨🇬 Lingala",
                "🇫🇷 Français"
            )

            if not francais:
                return None

            return GoogleTranslator(
                source="fr",
                target="en"
            ).translate(francais)

        if source == "🇬🇧 Anglais" and destination == "🇨🇬 Lingala":
            francais = GoogleTranslator(
                source="en",
                target="fr"
            ).translate(texte)

            if not francais:
                return None

            return rechercher_dans_dictionnaire(
                francais,
                "🇫🇷 Français",
                "🇨🇬 Lingala"
            )

        return None

    except Exception as e:
        print("Erreur traduction anglais :", e)
        return None

        # ==================== PRONONCER ====================

def prononcer_texte(texte, langue):

    if not texte.strip():
        return

    if not TTS_DISPONIBLE:
        print("TTS Android indisponible.")
        return

    try:

        activite = PythonActivity.mActivity

        tts = TextToSpeech(
            activite,
            None
        )

        # Choisir la langue
        if langue == "🇫🇷 Français":
            tts.setLanguage(Locale.FRENCH)

        elif langue == "🇬🇧 Anglais":
            tts.setLanguage(Locale.ENGLISH)

        elif langue == "🇨🇬 Lingala":
            # Android ne fournit pas forcément une voix Lingala.
            # On utilise le français comme solution de secours.
            tts.setLanguage(Locale.FRENCH)

        tts.speak(
            texte,
            TextToSpeech.QUEUE_FLUSH,
            None,
            "TRIKA_TTS"
        )

    except Exception as e:

        print("Erreur TTS Android :", e)

# ==================== VOIX ====================

CODE_VOIX = 1001
traducteur_actuel = None


def demander_permission_micro():

    if not ANDROID_DISPONIBLE:
        return

    try:
        request_permissions([
            Permission.RECORD_AUDIO
        ])
    except Exception as e:
        print("Permission microphone :", e)


def lancer_reconnaissance_vocale():

    if not ANDROID_DISPONIBLE:
        print("La reconnaissance vocale est disponible uniquement sur Android.")
        return

    try:

        demander_permission_micro()

        PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )

        RecognizerIntent = autoclass(
            "android.speech.RecognizerIntent"
        )

        activity_android = PythonActivity.mActivity

        intent = autoclass(
            "android.content.Intent"
        )(
            RecognizerIntent.ACTION_RECOGNIZE_SPEECH
        )

        intent.putExtra(
            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        )

        intent.putExtra(
            RecognizerIntent.EXTRA_PROMPT,
            "Parlez maintenant..."
        )

        intent.putExtra(
            RecognizerIntent.EXTRA_MAX_RESULTS,
            1
        )

        activity.bind(
            on_activity_result=recevoir_resultat_vocal
        )

        activity_android.startActivityForResult(
            intent,
            CODE_VOIX
        )

    except Exception as e:

        print("Erreur reconnaissance vocale :", e)


def recevoir_resultat_vocal(
    request_code,
    result_code,
    intent
):

    global traducteur_actuel

    if request_code != CODE_VOIX:
        return

    try:

        RecognizerIntent = autoclass(
            "android.speech.RecognizerIntent"
        )

        resultats = intent.getStringArrayListExtra(
            RecognizerIntent.EXTRA_RESULTS
        )

        if resultats is None or resultats.size() == 0:
            return

        texte_reconnu = str(
            resultats.get(0)
        )

        if traducteur_actuel is not None:

            traducteur_actuel.texte.text = texte_reconnu

            traducteur_actuel.traduire(None)

    except Exception as e:

        print(
            "Erreur lecture résultat vocal :",
            e
        )

class AccueilScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        principal = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(12), dp(14), dp(12)],
            spacing=dp(12)
        )

        entete = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(82), spacing=dp(8)
        )
        logo_path = fichier("logo.png")
        drapeau_path = DRAPEAU_PATH
        if os.path.exists(logo_path):
            entete.add_widget(Image(source=logo_path, size_hint_x=None, width=dp(72), allow_stretch=True, keep_ratio=True))
        else:
            entete.add_widget(Label(text="🤖", font_size=dp(38), size_hint_x=None, width=dp(72)))
        titre = BoxLayout(orientation="vertical")
        titre.add_widget(Label(text="TRIKA.TRAD", font_size=dp(23), bold=True, color=(0.24,0.10,0.34,1)))
        titre.add_widget(Label(text="Bienvenue dans votre assistant linguistique", font_size=dp(11), color=(0.35,0.30,0.38,1)))
        entete.add_widget(titre)
        if os.path.exists(drapeau_path):
            entete.add_widget(Image(source=drapeau_path, size_hint_x=None, width=dp(55), allow_stretch=True, keep_ratio=True))
        else:
            entete.add_widget(Label(text="🇨🇬", font_size=dp(30), size_hint_x=None, width=dp(55)))
        principal.add_widget(entete)

        principal.add_widget(Label(text="🎬 Présentation de TRIKA.TRAD", font_size=dp(18), bold=True, color=(0.32,0.16,0.45,1), size_hint_y=None, height=dp(35)))
        
        video_path = VIDEO_PATH

        if os.path.exists(video_path):
           from kivy.uix.video import Video
           video = Video(source=video_path, state="play", options={"eos": "loop"}, allow_stretch=True, keep_ratio=True, size_hint_y=1)
           principal.add_widget(video)
        else:
         card = Label(text="🎬 Vidéo de présentation introuvable.", font_size=dp(15), halign="center", valign="middle")
         card.bind(size=lambda inst, val: setattr(inst, "text_size", val))
         fond_arrondi(card, (1, 1, 1, 1), 24)
         principal.add_widget(card)
        
        principal.add_widget(Label(text="Découvrez TRIKA.TRAD et commencez une traduction.", font_size=dp(13), color=(0.35,0.30,0.38,1), size_hint_y=None, height=dp(32)))

        btn_trad = bouton_arrondi("📖  OUVRIR LE TRADUCTEUR", (0.32,0.16,0.45,1), 60)
        btn_trad.bind(on_press=lambda x: setattr(self.manager, "current", "traducteur"))
        principal.add_widget(btn_trad)

        # Navigation minimale de l'accueil
        menu = BoxLayout(orientation="horizontal", spacing=dp(5), size_hint_y=None, height=dp(58))
        btn_quiz = bouton_arrondi("🧠 Quiz", (0.55, 0.30, 0.20, 1), 50)
        btn_ia = bouton_arrondi("🤖 IA", (0.32,0.16,0.45,1), 50)
        btn_param = bouton_arrondi("⚙️ Paramètres", (0.55, 0.22, 0.28, 1), 50)
        btn_quiz.bind(on_press=lambda x: setattr(self.manager, "current", "quiz"))
        btn_ia.bind(on_press=lambda x: setattr(self.manager, "current", "ia"))
        btn_param.bind(on_press=lambda x: setattr(self.manager, "current", "parametres"))
        menu.add_widget(btn_quiz); menu.add_widget(btn_ia); menu.add_widget(btn_param)
        principal.add_widget(menu)
        self.add_widget(principal)
class TraducteurScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        principal = BoxLayout(
            orientation="vertical",
            padding=[dp(12), dp(10), dp(12), dp(8)],
            spacing=dp(8)
        )

        # =========================
        # EN-TÊTE
        # =========================

        entete = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(82),
            spacing=dp(8)
        )

        logo_path = fichier("logo.png")
        drapeau_path = fichier("congo.png")

        if os.path.exists(logo_path):
            entete.add_widget(
                Image(
                    source=logo_path,
                    size_hint_x=None,
                    width=dp(72),
                    allow_stretch=True,
                    keep_ratio=True
                )
            )
        else:
            entete.add_widget(
                Label(
                    text="🤖",
                    font_size=dp(38),
                    size_hint_x=None,
                    width=dp(72)
                )
            )

        titre = BoxLayout(orientation="vertical")

        titre.add_widget(
            Label(
                text="TRIKA.TRAD",
                font_size=dp(23),
                bold=True,
                color=(0.24, 0.10, 0.34, 1)
            )
        )

        titre.add_widget(
            Label(
                text="Lingala • Français • English",
                font_size=dp(11),
                color=(0.35, 0.30, 0.38, 1)
            )
        )

        entete.add_widget(titre)

        if os.path.exists(drapeau_path):
            entete.add_widget(
                Image(
                    source=drapeau_path,
                    size_hint_x=None,
                    width=dp(55),
                    allow_stretch=True,
                    keep_ratio=True
                )
            )
        else:
            entete.add_widget(
                Label(
                    text="🇨🇬",
                    font_size=dp(30),
                    size_hint_x=None,
                    width=dp(55)
                )
            )

        principal.add_widget(entete)

        # =========================
        # TITRE TRADUCTEUR
        # =========================

        principal.add_widget(
            Label(
                text="Traducteur Lingala • Français • Anglais",
                font_size=dp(13),
                color=(0.25, 0.30, 0.35, 1),
                size_hint_y=None,
                height=dp(28)
            )
        )

        # =========================
        # LANGUES
        # =========================

        langues = BoxLayout(
            orientation="horizontal",
            spacing=dp(6),
            size_hint_y=None,
            height=dp(48)
        )

        self.langue_source = Spinner(
            text="🇫🇷 Français",
            values=("🇫🇷 Français", "🇨🇬 Lingala", "🇬🇧 Anglais"),
            font_size=dp(14)
        )

        fleche = Label(
            text="⇄",
            font_size=dp(23),
            bold=True,
            size_hint_x=None,
            width=dp(38)
        )

        self.langue_destination = Spinner(
            text="🇨🇬 Lingala",
            values=("🇨🇬 Lingala", "🇫🇷 Français", "🇬🇧 Anglais"),
            font_size=dp(14)
        )

        langues.add_widget(self.langue_source)
        langues.add_widget(fleche)
        langues.add_widget(self.langue_destination)

        principal.add_widget(langues)

        # =========================
        # TEXTE
        # =========================

        principal.add_widget(
            Label(
                text="Texte à traduire",
                font_size=dp(14),
                color=(0.24,0.10,0.34,1),
                bold=True,
                size_hint_y=None,
                height=dp(25)
            )
        )

        self.texte = TextInput(
            hint_text="Écris un mot ou une phrase...",
            multiline=True,
            font_size=dp(16),
            size_hint_y=None,
            height=dp(105),
            padding=[dp(12), dp(12)]
        )

        principal.add_widget(self.texte)

        # =========================
        # BOUTON TRADUIRE
        # =========================

        bouton_traduire = bouton_arrondi(
            "✨ TRADUCTEUR",
            (0.32, 0.16, 0.45, 1),
            56
        )

        bouton_traduire.bind(on_press=self.traduire)
        principal.add_widget(bouton_traduire)

        # =========================
        # RÉSULTAT
        # =========================

        principal.add_widget(
            Label(
                text="Résultat",
                font_size=dp(14),
                color=(0.24,0.10,0.34,1),
                bold=True,
                size_hint_y=None,
                height=dp(25)
            )
        )

        self.resultat = Label(
            text="",
            font_size=dp(16),
            color=(0.15, 0.15, 0.15, 1),
            size_hint_y=None,
            height=dp(110),
            halign="left",
            valign="top",
            text_size=(Window.width - dp(40), None)
        )

        champ_style(self.resultat)
        principal.add_widget(self.resultat)

        # =========================
        # BOUTONS ACTIONS
        # =========================

        boutons = BoxLayout(
            orientation="horizontal",
            spacing=dp(7),
            size_hint_y=None,
            height=dp(48)
        )

        bouton_copier = Button(
            text="📋 Copier",
            font_size=dp(14)
        )

        bouton_prononcer = Button(
            text="🔊 Écouter",
            font_size=dp(14)
        )

        bouton_parler = Button(
            text="🎤 Parler",
            font_size=dp(14)
        )

        bouton_copier.bind(on_press=self.copier)
        bouton_prononcer.bind(on_press=self.prononcer)
        bouton_parler.bind(on_press=self.parler)

        boutons.add_widget(bouton_copier)
        boutons.add_widget(bouton_prononcer)
        boutons.add_widget(bouton_parler)

        principal.add_widget(boutons)

        # =========================
        # VIDÉO
        # =========================

        video_path = fichier("presentation.mp4")

        if os.path.exists(video_path):
            from kivy.uix.video import Video

            video = Video(
                source=video_path,
                state="play",
                options={"eos": "loop"},
                size_hint_y=None,
                height=dp(105)
            )

            principal.add_widget(video)

        else:
            video_card = Label(
                text="🎬 VIDÉO DE PRÉSENTATION TRIKA.TRAD",
                font_size=dp(13),
                bold=True,
                color=(0.32, 0.16, 0.45, 1),
                size_hint_y=None,
                height=dp(58)
            )

            fond_arrondi(video_card, (1, 1, 1, 1), 20)
            principal.add_widget(video_card)

        # =========================
        # ESPACE
        # =========================

        principal.add_widget(
            Label(
                text="",
                size_hint_y=1
            )
        )

        # =========================
        # MENU
        # =========================

        menu = BoxLayout(
            orientation="horizontal",
            spacing=dp(4),
            size_hint_y=None,
            height=dp(62)
        )

        btn_accueil = bouton_arrondi("🏠 Accueil", (0.32, 0.16, 0.45, 1), 58)
        btn_quiz = bouton_arrondi("🧠 Quiz", (0.55, 0.30, 0.20, 1), 58)
        btn_ia = bouton_arrondi("🤖 TRIKA IA", (0.20, 0.40, 0.48, 1), 58)
        btn_parametres = bouton_arrondi("⚙️ Paramètres", (0.55, 0.22, 0.28, 1), 58)

        btn_accueil.bind(on_press=lambda x: setattr(self.manager, "current", "accueil"))
        btn_quiz.bind(on_press=lambda x: setattr(self.manager, "current", "quiz"))
        btn_ia.bind(on_press=lambda x: setattr(self.manager, "current", "ia"))
        btn_parametres.bind(on_press=lambda x: setattr(self.manager, "current", "parametres"))

        menu.add_widget(btn_accueil)
        menu.add_widget(btn_quiz)
        menu.add_widget(btn_ia)
        menu.add_widget(btn_parametres)

        principal.add_widget(menu)

        principal.opacity = 0

        self.add_widget(principal)

        Animation(
           opacity=1,
           duration=0.5
        ).start(principal)

    # ==================================================
    # TRADUCTION
    # ==================================================

    def traduire(self, instance):
        texte = self.texte.text.strip()

        if not texte:
            self.resultat.text = "Écris d'abord un mot ou une phrase."
            return

        source = self.langue_source.text
        destination = self.langue_destination.text

        if source == destination:
            self.resultat.text = "Choisis deux langues différentes."
            return

        resultat = rechercher_dans_dictionnaire(
            texte,
            source,
            destination
        )

        if resultat is None and ("🇬🇧 Anglais" in (source, destination)):
            resultat = traduire_anglais(
                texte,
                source,
                destination
            )

        if resultat is None:

            if not os.path.exists(DB_PATH):
                self.resultat.text = "❌ dictionnaire.db est introuvable."
                return

            if "🇬🇧 Anglais" in (source, destination):
                self.resultat.text = "❌ Traduction impossible. Vérifie ta connexion Internet."
                return

            self.resultat.text = "❌ Aucun résultat fiable dans le dictionnaire TRIKA.TRAD."
            return

        self.resultat.text = resultat

        enregistrer_historique(
            texte,
            resultat,
            source,
            destination
        )

    # ==================================================
    # PRONONCER
    # ==================================================

    def prononcer(self, instance):

        texte = self.resultat.text.strip()

        if not texte:
            return

        if texte.startswith("❌") or texte.startswith("ℹ️"):
            return

        if texte.startswith("Traduction :"):
            texte = texte.replace(
                "Traduction :",
                "",
                1
            ).strip()

        langue = self.langue_destination.text

        prononcer_texte(
            texte,
            langue
        )

    def parler(self, instance):

        global traducteur_actuel

        traducteur_actuel = self

        lancer_reconnaissance_vocale()

    # ==================================================
    # COPIER
    # ==================================================

    def copier(self, instance):

        Clipboard.copy(self.resultat.text)

        self.resultat.text += "\n\n✅ Copié !"
class QuizScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.score_qcm = 0
        self.numero_qcm = 0
        self.bonne_reponse = ""
        self.choix_qcm = []

        self.score_melange = 0
        self.numero_melange = 0
        self.mot_correct = ""

        self.mots = self.charger_mots()

        # Listes séparées et mélangées pour chaque jeu
        self.questions_qcm = []
        self.questions_melange = []

        self.construire_menu_jeux()
        self.construire_qcm()
        self.construire_melange()

        self.afficher_menu_jeux()

    # =====================================================
    # CHARGER LES MOTS DE SQLITE
    # =====================================================

    def charger_mots(self):

        if not os.path.exists(DB_PATH):
            return []

        try:

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute("""
                SELECT francais, lingala
                FROM dictionnaire
                WHERE francais IS NOT NULL
                AND lingala IS NOT NULL
                AND TRIM(francais) != ''
                AND TRIM(lingala) != ''
            """)

            mots = cur.fetchall()

            conn.close()

            # Supprimer les doublons
            mots_uniques = list(dict.fromkeys(mots))

            return mots_uniques

        except Exception as e:

            print("Erreur chargement dictionnaire :", e)

            return []

    # =====================================================
    # ACTUALISER LES MOTS
    # =====================================================

    def actualiser_mots(self):

        self.mots = self.charger_mots()

        self.questions_qcm = self.mots.copy()
        self.questions_melange = self.mots.copy()

        random.shuffle(self.questions_qcm)
        random.shuffle(self.questions_melange)

    # =====================================================
    # MENU DES JEUX
    # =====================================================

    def construire_menu_jeux(self):

        self.menu_jeux = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12)
        )

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(70),
            spacing=dp(6)
        )

        logo = fichier("logo.png")
        drapeau_path = DRAPEAU_PATH

        if os.path.exists(logo):

            header.add_widget(
                Image(
                    source=logo,
                    size_hint_x=None,
                    width=dp(60),
                    allow_stretch=True,
                    keep_ratio=True
                )
            )

        else:

            header.add_widget(
                Label(
                    text="🤖",
                    font_size=dp(30),
                    size_hint_x=None,
                    width=dp(60)
                )
            )

        header.add_widget(
            Label(
                text="🧠 QUIZ TRIKA.TRAD",
                font_size=dp(22),
                bold=True,
                color=(0.32, 0.16, 0.45, 1)
            )
        )

        if os.path.exists(drapeau_path):

            header.add_widget(
                Image(
                    source=drapeau_path,
                    size_hint_x=None,
                    width=dp(50),
                    allow_stretch=True,
                    keep_ratio=True
                )
            )

        else:

            header.add_widget(
                Label(
                    text="🇨🇬",
                    font_size=dp(26),
                    size_hint_x=None,
                    width=dp(50)
                )
            )

        self.menu_jeux.add_widget(header)

        self.menu_jeux.add_widget(
            Label(
                text="Choisis ton jeu",
                font_size=dp(18),
                color=(0.24,0.10,0.34,1),
                bold=True,
                size_hint_y=None,
                height=dp(40)
            )
        )

        # =========================
        # QCM
        # =========================

        btn_qcm = bouton_arrondi(
            "📖  QCM",
            (0.32, 0.16, 0.45, 1),
            65
        )

        btn_qcm.bind(
            on_press=lambda x: self.ouvrir_qcm()
        )

        self.menu_jeux.add_widget(
            btn_qcm
        )

        # =========================
        # MOT MÉLANGÉ
        # =========================

        btn_melange = bouton_arrondi(
            "🔀  MOT MÉLANGÉ",
            (0.20, 0.40, 0.48, 1),
            65
        )

        btn_melange.bind(
            on_press=lambda x: self.ouvrir_melange()
        )

        self.menu_jeux.add_widget(
            btn_melange
        )

        self.menu_jeux.add_widget(
            Label(
                text="",
                size_hint_y=1
            )
        )

        retour = bouton_arrondi(
            "🏠  Retour à l'accueil",
            (0.55, 0.22, 0.28, 1),
            55
        )

        retour.bind(
            on_press=lambda x: setattr(
                self.manager,
                "current",
                "accueil"
            )
        )

        self.menu_jeux.add_widget(
            retour
        )

    # =====================================================
    # CONSTRUIRE QCM
    # =====================================================

    def construire_qcm(self):

        self.page_qcm = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        self.page_qcm.add_widget(
            Label(
                text="📖 QCM",
                font_size=dp(24),
                bold=True,
                color=(0.32, 0.16, 0.45, 1),
                size_hint_y=None,
                height=dp(55)
            )
        )

        self.question_qcm = Label(
            text="",
            font_size=dp(19),
            bold=True
        )

        self.page_qcm.add_widget(
            self.question_qcm
        )

        self.score_qcm_label = Label(
            text="Score : 0",
            font_size=dp(15),
            size_hint_y=None,
            height=dp(35)
        )

        self.page_qcm.add_widget(
            self.score_qcm_label
        )

        self.btn_a = bouton_arrondi(
            "",
            (0.32, 0.16, 0.45, 1),
            55
        )

        self.btn_b = bouton_arrondi(
            "",
            (0.20, 0.40, 0.48, 1),
            55
        )

        self.btn_c = bouton_arrondi(
            "",
            (0.55, 0.30, 0.20, 1),
            55
        )

        self.btn_a.bind(
            on_press=lambda x: self.verifier_qcm(0)
        )

        self.btn_b.bind(
            on_press=lambda x: self.verifier_qcm(1)
        )

        self.btn_c.bind(
            on_press=lambda x: self.verifier_qcm(2)
        )

        self.page_qcm.add_widget(self.btn_a)
        self.page_qcm.add_widget(self.btn_b)
        self.page_qcm.add_widget(self.btn_c)

        self.feedback_qcm = Label(
            text="",
            font_size=dp(15),
            size_hint_y=None,
            height=dp(65)
        )

        self.page_qcm.add_widget(
            self.feedback_qcm
        )

        self.page_qcm.add_widget(
            Label(
                text="",
                size_hint_y=1
            )
        )

        retour = bouton_arrondi(
            "⬅ Retour aux jeux",
            (0.55, 0.22, 0.28, 1),
            52
        )

        retour.bind(
            on_press=lambda x: self.afficher_menu_jeux()
        )

        self.page_qcm.add_widget(
            retour
        )

    # =====================================================
    # NOUVELLE QUESTION QCM
    # =====================================================

    def nouvelle_question_qcm(self):

        if len(self.questions_qcm) < 3:

            self.question_qcm.text = (
                "❌ Pas assez de mots dans le dictionnaire."
            )

            self.feedback_qcm.text = (
                "Le QCM nécessite au moins 3 mots."
            )

            return

        if self.numero_qcm >= len(self.questions_qcm):

            self.question_qcm.text = (
                "🎉 QCM terminé !"
            )

            self.feedback_qcm.text = (
                f"🏆 Score final : "
                f"{self.score_qcm}/{len(self.questions_qcm)}"
            )

            self.btn_a.text = "🔄 Relancer le QCM"
            self.btn_b.text = ""
            self.btn_c.text = ""

            self.btn_a.disabled = False
            self.btn_b.disabled = True
            self.btn_c.disabled = True

            return

        # Prendre le mot dans la liste déjà mélangée
        francais, lingala = self.questions_qcm[
            self.numero_qcm
        ]

        self.bonne_reponse = lingala

        # Chercher de mauvaises réponses
        autres = [
            mot_lingala
            for mot_francais, mot_lingala
            in self.questions_qcm
            if mot_lingala != lingala
        ]

        if len(autres) < 2:

            self.question_qcm.text = (
                "❌ Pas assez de réponses différentes."
            )

            return

        mauvaises = random.sample(
            autres,
            2
        )

        self.choix_qcm = [
            self.bonne_reponse,
            mauvaises[0],
            mauvaises[1]
        ]

        # Mélanger les trois réponses
        random.shuffle(
            self.choix_qcm
        )

        self.question_qcm.text = (
            f"Comment dit-on « {francais} » "
            f"en Lingala ?"
        )

        self.btn_a.text = (
            f"A. {self.choix_qcm[0]}"
        )

        self.btn_b.text = (
            f"B. {self.choix_qcm[1]}"
        )

        self.btn_c.text = (
            f"C. {self.choix_qcm[2]}"
        )

        self.btn_a.disabled = False
        self.btn_b.disabled = False
        self.btn_c.disabled = False

        self.feedback_qcm.text = ""

    # =====================================================
    # VERIFIER QCM
    # =====================================================

    def verifier_qcm(self, index):

        # Relancer le quiz lorsqu'il est terminé
        if (
            self.numero_qcm >= len(self.questions_qcm)
            and index == 0
        ):

            self.ouvrir_qcm()

            return

        if not self.choix_qcm:
            return

        boutons = [
            self.btn_a,
            self.btn_b,
            self.btn_c
        ]

        bouton_choisi = boutons[index]

        reponse = self.choix_qcm[index]

        self.btn_a.disabled = True
        self.btn_b.disabled = True
        self.btn_c.disabled = True

        if reponse == self.bonne_reponse:

            self.score_qcm += 1

            bouton_choisi.text = (
                f"✅ {bouton_choisi.text}"
            )

            self.feedback_qcm.text = (
                "🎉 Bravo ! Bonne réponse."
            )

        else:

            bouton_choisi.text = (
                f"❌ {bouton_choisi.text}"
            )

            self.feedback_qcm.text = (
                "❌ Mauvaise réponse !\n"
                f"✅ Bonne réponse : "
                f"{self.bonne_reponse}"
            )

            for i, choix in enumerate(
                self.choix_qcm
            ):

                if choix == self.bonne_reponse:

                    boutons[i].text = (
                        f"✅ {boutons[i].text}"
                    )

        self.score_qcm_label.text = (
            f"Score : {self.score_qcm}"
        )

        from kivy.clock import Clock

        self.numero_qcm += 1

        Clock.schedule_once(
            lambda dt: self.nouvelle_question_qcm(),
            1.8
        )

    # =====================================================
    # CONSTRUIRE MOT MÉLANGÉ
    # =====================================================

    def construire_melange(self):

        self.page_melange = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(12)
        )

        self.page_melange.add_widget(
            Label(
                text="🔀 MOT MÉLANGÉ",
                font_size=dp(24),
                bold=True,
                color=(0.32, 0.16, 0.45, 1),
                size_hint_y=None,
                height=dp(55)
            )
        )

        self.indice_melange = Label(
            text="",
            font_size=dp(16)
        )

        self.page_melange.add_widget(
            self.indice_melange
        )

        self.mot_melange = Label(
            text="",
            font_size=dp(30),
            bold=True,
            color=(0.32, 0.16, 0.45, 1),
            size_hint_y=None,
            height=dp(70)
        )

        self.page_melange.add_widget(
            self.mot_melange
        )

        self.reponse_melange = TextInput(
            hint_text="Écris le mot correct...",
            multiline=False,
            font_size=dp(17),
            size_hint_y=None,
            height=dp(55)
        )

        self.page_melange.add_widget(
            self.reponse_melange
        )

        btn_valider = bouton_arrondi(
            "✅ VALIDER",
            (0.32, 0.16, 0.45, 1),
            55
        )

        btn_valider.bind(
            on_press=lambda x: self.verifier_melange()
        )

        self.page_melange.add_widget(
            btn_valider
        )

        self.feedback_melange = Label(
            text="",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(60)
        )

        self.page_melange.add_widget(
            self.feedback_melange
        )

        self.score_melange_label = Label(
            text="Score : 0",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(35)
        )

        self.page_melange.add_widget(
            self.score_melange_label
        )

        self.page_melange.add_widget(
            Label(
                text="",
                size_hint_y=1
            )
        )

        retour = bouton_arrondi(
            "⬅ Retour aux jeux",
            (0.55, 0.22, 0.28, 1),
            52
        )

        retour.bind(
            on_press=lambda x: self.afficher_menu_jeux()
        )

        self.page_melange.add_widget(
            retour
        )

    # =====================================================
    # NOUVEAU MOT MÉLANGÉ
    # =====================================================

    def nouveau_melange(self):

        if not self.questions_melange:

            self.mot_melange.text = (
                "❌ Dictionnaire vide."
            )

            return

        if self.numero_melange >= len(
            self.questions_melange
        ):

            self.mot_melange.text = (
                "🎉 Jeu terminé !"
            )

            self.feedback_melange.text = (
                f"🏆 Score final : "
                f"{self.score_melange}/"
                f"{len(self.questions_melange)}"
            )

            return

        francais, lingala = self.questions_melange[
            self.numero_melange
        ]

        self.mot_correct = lingala.strip()

        lettres = list(self.mot_correct)

        # Mélanger les lettres
        if len(lettres) > 1:

            melange = self.mot_correct

            tentatives = 0

            while (
                melange.lower()
                == self.mot_correct.lower()
                and tentatives < 10
            ):

                random.shuffle(lettres)

                melange = "".join(
                    lettres
                )

                tentatives += 1

        else:

            melange = self.mot_correct

        self.indice_melange.text = (
            f"🇫🇷 Indice : {francais}"
        )

        self.mot_melange.text = (
            melange.upper()
        )

        self.reponse_melange.text = ""

        self.feedback_melange.text = ""

    # =====================================================
    # VERIFIER MOT MÉLANGÉ
    # =====================================================

    def verifier_melange(self):

        if self.numero_melange >= len(
            self.questions_melange
        ):

            self.ouvrir_melange()

            return

        reponse = (
            self.reponse_melange.text
            .strip()
            .lower()
        )

        if not reponse:

            self.feedback_melange.text = (
                "✏️ Écris une réponse."
            )

            return

        if reponse == self.mot_correct.lower():

            self.score_melange += 1

            self.feedback_melange.text = (
                "✅ Bravo ! Bonne réponse."
            )

        else:

            self.feedback_melange.text = (
                "❌ Mauvaise réponse.\n"
                f"✅ La bonne réponse était : "
                f"{self.mot_correct}"
            )

        self.score_melange_label.text = (
            f"Score : {self.score_melange}"
        )

        from kivy.clock import Clock

        self.numero_melange += 1

        Clock.schedule_once(
            lambda dt: self.nouveau_melange(),
            1.8
        )

    # =====================================================
    # OUVRIR QCM
    # =====================================================

    def ouvrir_qcm(self):

        # Relire la base à chaque nouveau lancement
        self.actualiser_mots()

        self.clear_widgets()

        self.add_widget(
            self.page_qcm
        )

        self.score_qcm = 0
        self.numero_qcm = 0
        self.bonne_reponse = ""
        self.choix_qcm = []

        # Mélanger encore une fois
        random.shuffle(
            self.questions_qcm
        )

        self.score_qcm_label.text = (
            "Score : 0"
        )

        self.nouvelle_question_qcm()

    # =====================================================
    # OUVRIR MOT MÉLANGÉ
    # =====================================================

    def ouvrir_melange(self):

        # Relire la base à chaque nouveau lancement
        self.actualiser_mots()

        self.clear_widgets()

        self.add_widget(
            self.page_melange
        )

        self.score_melange = 0
        self.numero_melange = 0
        self.mot_correct = ""

        # Mélanger encore une fois
        random.shuffle(
            self.questions_melange
        )

        self.score_melange_label.text = (
            "Score : 0"
        )

        self.nouveau_melange()

    # =====================================================
    # RETOUR MENU JEUX
    # =====================================================

    def afficher_menu_jeux(self):

        self.clear_widgets()

        self.add_widget(
            self.menu_jeux
        )

class IAScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # =========================
        # LAYOUT PRINCIPAL
        # =========================

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        # =========================
        # EN-TÊTE
        # =========================

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(62),
            spacing=dp(6)
        )

        logo = fichier("logo.png")
        drapeau = fichier("drapeau.png")

        if os.path.exists(logo):
            header.add_widget(
                Image(
                    source=logo,
                    size_hint_x=None,
                    width=dp(58),
                    allow_stretch=True,
                    keep_ratio=True
                )
            )
        else:
            header.add_widget(
                Label(
                    text="🤖",
                    font_size=dp(30),
                    size_hint_x=None,
                    width=dp(58)
                )
            )

        header.add_widget(
            Label(
                text="🤖 TRIKA IA",
                font_size=dp(20),
                bold=True,
                color=(0.32, 0.16, 0.45, 1)
            )
        )

        if os.path.exists(drapeau):
            header.add_widget(
                Image(
                    source=drapeau,
                    size_hint_x=None,
                    width=dp(48),
                    allow_stretch=True,
                    keep_ratio=True
                )
            )
        else:
            header.add_widget(
                Label(
                    text="🇨🇬",
                    font_size=dp(26),
                    size_hint_x=None,
                    width=dp(48)
                )
            )

        layout.add_widget(header)

        # =========================
        # DESCRIPTION
        # =========================

        layout.add_widget(
            Label(
                text="Pose ta question à TRIKA IA",
                font_size=dp(14),
                size_hint_y=None,
                height=dp(30)
            )
        )

        # =========================
        # ZONE QUESTION
        # =========================
        self.question = TextInput(
            hint_text="Écris ta question en français ou en lingala..",
            multiline=True,
            font_size=dp(16),
            size_hint_y=None,
            height=dp(105),
            padding=[dp(12), dp(12)]
        )
        
       

        champ_style(self.question)

        layout.add_widget(
            self.question
        )

        # =========================
        # BOUTON
        # =========================

        self.bouton = bouton_arrondi(
            "🤖 DEMANDER À TRIKA",
            (0.32, 0.16, 0.45, 1),
            58
        )

        self.bouton.bind(
            on_press=self.demander
        )

        layout.add_widget(
            self.bouton
        )

        # =========================
        # ZONE DE CHAT
        # =========================

        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(6)
        )

        self.chat_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(5), dp(5), dp(5), dp(10)],
            size_hint_y=None
        )

        self.chat_layout.bind(
            minimum_height=self.chat_layout.setter("height")
        )

        self.scroll.add_widget(
            self.chat_layout
        )

        layout.add_widget(
            self.scroll
        )

        # =========================
        # MESSAGE INITIAL
        # =========================

        self.ajouter_message(
            "🤖 TRIKA IA",
            "Bonjour ! Je suis TRIKA IA.\n"
            "Pose-moi une question en français ou en lingala.",
            ia=True
        )

        # =========================
        # RETOUR
        # =========================

        retour = bouton_arrondi(
            "🏠 Retour à l'accueil",
            (0.55, 0.22, 0.28, 1),
            52
        )

        retour.bind(
            on_press=lambda x: setattr(
                self.manager,
                "current",
                "accueil"
            )
        )

        layout.add_widget(
            retour
        )

        # =========================
        # AJOUT DE L'ÉCRAN
        # =========================

        self.add_widget(
            layout
        )

    # ==================================================
    # AJOUTER UN MESSAGE
    # ==================================================

    def ajouter_message(self, auteur, message, ia=False):

        # =========================
        # COULEUR
        # =========================

        if ia:
            couleur = (0.88, 0.96, 0.88, 1)
        else:
            couleur = (0.88, 0.92, 1, 1)

        # =========================
        # BULLE
        # =========================

        boite = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            size_hint_x=1,
            padding=[dp(12), dp(10), dp(12), dp(10)]
        )

        # =========================
        # TEXTE
        # =========================

        texte = Label(
            text=f"[b]{auteur}[/b]\n{message}",
            markup=True,
            halign="left",
            valign="top",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            size_hint_x=1
        )

        # Largeur disponible pour le retour à la ligne
        def ajuster_largeur(instance, width):

            texte.text_size = (
                max(dp(50), width - dp(24)),
                None
            )

        texte.bind(
            width=ajuster_largeur
        )

        # Hauteur automatique selon la quantité de texte
        texte.bind(
            texture_size=lambda instance, value: setattr(
                instance,
                "height",
                value[1]
            )
        )

        # =========================
        # HAUTEUR DE LA BULLE
        # =========================

        def ajuster_hauteur(instance, value):

            boite.height = (
                texte.height
                + dp(20)
            )

        texte.bind(
            height=ajuster_hauteur
        )

        # =========================
        # FOND ARRONDI
        # =========================

        from kivy.graphics import Color, RoundedRectangle

        with boite.canvas.before:

            Color(
                *couleur
            )

            boite.rect = RoundedRectangle(
                pos=boite.pos,
                size=boite.size,
                radius=[15]
            )

        def maj_rect(instance, value):

            boite.rect.pos = instance.pos
            boite.rect.size = instance.size

        boite.bind(
            pos=maj_rect,
            size=maj_rect
        )

        # =========================
        # AJOUT DU TEXTE
        # =========================

        boite.add_widget(
            texte
        )

        # =========================
        # AJOUT AU CHAT
        # =========================

        self.chat_layout.add_widget(
            boite
        )

        # =========================
        # FORCER LE CALCUL
        # =========================

        Clock.schedule_once(
            lambda dt: self.mettre_a_jour_bulle(
                boite,
                texte
            ),
            0
        )

        # =========================
        # DESCENDRE EN BAS
        # =========================

        Clock.schedule_once(
            lambda dt: setattr(
                self.scroll,
                "scroll_y",
                0
            ),
            0.2
        )

    # ==================================================
    # MISE À JOUR BULLE
    # ==================================================

    def mettre_a_jour_bulle(self, boite, texte):

        largeur = boite.width

        if largeur <= 0:
            largeur = self.chat_layout.width

        texte.text_size = (
            max(dp(50), largeur - dp(24)),
            None
        )

        boite.height = (
            texte.texture_size[1]
            + dp(20)
        )

    # ==================================================
    # DEMANDER À TRIKA
    # ==================================================

    def demander(self, instance):

        question = self.question.text.strip()

        if not question:

            self.ajouter_message(
                "⚠️ TRIKA IA",
                "Écris d'abord une question.",
                ia=True
            )

            return

        # =========================
        # AFFICHER QUESTION
        # =========================

        self.ajouter_message(
            "👤 Vous",
            question,
            ia=False
        )

        # =========================
        # BLOQUER LE BOUTON
        # =========================

        self.bouton.disabled = True

        self.bouton.text = (
            "⏳ TRIKA RÉFLÉCHIT..."
        )

        # =========================
        # THREAD IA
        # =========================

        thread = threading.Thread(
            target=self._appel_ia,
            args=(question,),
            daemon=True
        )

        thread.start()

    # ==================================================
    # APPEL À L'IA
    # ==================================================

    def _appel_ia(self, question):

        try:

            resultat = demander_a_trika(
                question
            )

        except Exception as e:

            resultat = (
                "❌ TRIKA IA n'est pas disponible.\n\n"
                "Vérifie la connexion au service IA.\n\n"
                f"Détail : {e}"
            )

        Clock.schedule_once(
            lambda dt: self.afficher_reponse(
                resultat
            ),
            0
        )

    # ==================================================
    # AFFICHER RÉPONSE
    # ==================================================

    def afficher_reponse(self, resultat):

        self.ajouter_message(
            "🤖 TRIKA IA",
            str(resultat),
            ia=True
        )

        # =========================
        # VIDER QUESTION
        # =========================

        self.question.text = ""

        # =========================
        # RÉACTIVER
        # =========================

        self.bouton.disabled = False

        self.bouton.text = (
            "🤖 DEMANDER À TRIKA"
        )
class ParametresScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(70), spacing=dp(6))

        logo = fichier("logo.png")
        logo_path = LOGO_PATH

        if os.path.exists(logo):
            header.add_widget(Image(source=logo, size_hint_x=None, width=dp(58), allow_stretch=True, keep_ratio=True))
        else:
            header.add_widget(Label(text="🤖", font_size=dp(30), size_hint_x=None, width=dp(58)))

        header.add_widget(Label(text="⚙️ PARAMÈTRES", font_size=dp(22), bold=True, color=(0.32, 0.16, 0.45, 1)))

        
        layout.add_widget(header)

        layout.add_widget(Label(text="Personnalise ton expérience TRIKA.TRAD",color=(0.24,0.10,0.34,1), font_size=dp(15), size_hint_y=None, height=dp(35)))

        btn_apparence = bouton_arrondi("🎨  Apparence", (0.32, 0.16, 0.45, 1), 62)
        btn_historique = bouton_arrondi("📜  Historique", (0.20, 0.40, 0.48, 1), 62)
        btn_apropos = bouton_arrondi("ℹ️  À propos", (0.55, 0.30, 0.20, 1), 62)

        btn_apparence.bind(on_press=lambda x: setattr(self.manager, "current", "apparence"))
        btn_historique.bind(on_press=lambda x: setattr(self.manager, "current", "historique"))
        btn_apropos.bind(on_press=lambda x: setattr(self.manager, "current", "apropos"))

        layout.add_widget(btn_apparence)
        layout.add_widget(btn_historique)
        layout.add_widget(btn_apropos)

        layout.add_widget(Label(text="", size_hint_y=1))

        retour = bouton_arrondi("🏠  Retour à l'accueil", (0.55, 0.22, 0.28, 1), 55)
        retour.bind(on_press=lambda x: setattr(self.manager, "current", "accueil"))
        layout.add_widget(retour)

        self.add_widget(layout)

class ApparenceScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.animation_active = False

        layout = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))

        layout.add_widget(Label(text="🎨 APPARENCE", font_size=dp(24), bold=True, color=(0.32, 0.16, 0.45, 1), size_hint_y=None, height=dp(55)))

        layout.add_widget(Label(text="Choisis l'apparence de TRIKA.TRAD", font_size=dp(15), size_hint_y=None, height=dp(30)))

        btn_clair = bouton_arrondi("☀️  Mode clair", (0.70, 0.55, 0.20, 1), 58)
        btn_sombre = bouton_arrondi("🌙  Mode sombre", (0.16, 0.12, 0.22, 1), 58)
        

        btn_clair.bind(on_press=lambda x: self.changer_theme("clair"))
        btn_sombre.bind(on_press=lambda x: self.changer_theme("sombre"))
        

        layout.add_widget(btn_clair)
        layout.add_widget(btn_sombre)
        

        self.logo_animation = Label(text="🤖 TRIKA", font_size=dp(30), bold=True, size_hint_y=None, height=dp(80))
        layout.add_widget(self.logo_animation)

        layout.add_widget(Label(text="", size_hint_y=1))

        retour = bouton_arrondi("⬅ Retour aux paramètres", (0.32, 0.16, 0.45, 1), 55)
        retour.bind(on_press=lambda x: setattr(self.manager, "current", "parametres"))
        layout.add_widget(retour)

        self.add_widget(layout)

    def changer_theme(self, mode):

        app = App.get_running_app()

        if mode == "sombre":
            app.theme_mode = "sombre"
            Window.clearcolor = (0.07, 0.05, 0.10, 1)
        else:
            app.theme_mode = "clair"
            Window.clearcolor = (0.97, 0.96, 0.99, 1)

    def changer_animation(self):

        from kivy.animation import Animation

        if self.animation_active:
            self.animation_active = False
            Animation.cancel_all(self.logo_animation)
            self.logo_animation.opacity = 1
            return

        self.animation_active = True

        animation = Animation(opacity=0.25, duration=0.6) + Animation(opacity=1, duration=0.6)
        animation.repeat = True
        animation.start(self.logo_animation)
class AproposScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10))

        layout.add_widget(Label(text="ℹ️ À PROPOS DE TRIKA.TRAD", font_size=dp(22), bold=True, color=(0.32, 0.16, 0.45, 1), size_hint_y=None, height=dp(55)))

        self.texte = TextInput(
            readonly=True,
            multiline=True,
            font_size=dp(14),
            text="""À PROPOS DE TRIKA.TRAD
📱 Nom de l’application

TRIKA.TRAD est une application de traduction conçue pour faciliter la compréhension et la communication entre le lingala, le français et l’anglais.

Son nom vient de TRIKA.TECH, une initiative orientée vers la création de solutions numériques adaptées aux besoins locaux.

👨‍💻 Création de l’application

TRIKA.TRAD a été créée par EBA Christ Pacifique, développeur et étudiant en 3ᵉ année d’Économie Numérique.

L’application est développée dans le cadre d’une démarche visant à mettre les technologies numériques au service de la valorisation des langues locales, en particulier le lingala.

🎯 But de l’application

L'objectif principal de TRIKA.TRAD est de proposer un outil simple et accessible permettant de :

traduire des mots et des phrases ;
faciliter la communication entre locuteurs du lingala et du français ;
aider les utilisateurs à comprendre certains termes et expressions ;
contribuer à la valorisation et à la numérisation du lingala ;
permettre progressivement l'utilisation du lingala dans les outils numériques modernes.

TRIKA.TRAD ne cherche pas seulement à traduire des mots : elle cherche également à tenir compte du contexte dans lequel les mots sont utilisés.

⚙️ Comment fonctionne TRIKA.TRAD ?

TRIKA.TRAD combine plusieurs mécanismes de traduction.

L'application possède notamment une base de données de mots et de correspondances linguistiques permettant d'effectuer certaines traductions directement, sans avoir besoin d'une connexion Internet.

Lorsqu'une traduction ne peut pas être trouvée directement dans les données disponibles, l'application peut utiliser des mécanismes complémentaires, notamment l'intelligence artificielle et les services de traduction en ligne lorsqu'ils sont disponibles.

L'application propose également des fonctionnalités telles que :

🔎 recherche et suggestions de mots ;
📖 traduction de mots et de phrases ;
📋 copie du résultat ;
🔊 lecture audio de certaines traductions ;
🕘 historique des traductions ;
🌍 traduction entre plusieurs langues ;
🤖 assistance par intelligence artificielle lorsque cette fonction est disponible.
🗣️ Le lingala : une langue fortement contextuelle

Le lingala est une langue dans laquelle le contexte joue un rôle très important.

Un même mot ou une même expression peut parfois prendre une signification différente selon :

le contexte de la conversation ;
la personne qui parle ;
la situation ;
le lieu ou la région ;
l'époque ;
le niveau de langue utilisé ;
la manière dont le mot est prononcé ou associé à d'autres mots.

Ainsi, une traduction mot à mot ne permet pas toujours de transmettre exactement le sens recherché.

Par exemple, une expression peut avoir un sens particulier dans une conversation quotidienne, alors qu'elle peut être comprise différemment dans un contexte professionnel, culturel ou traditionnel.

C'est pourquoi les résultats proposés par TRIKA.TRAD doivent parfois être interprétés en fonction du contexte.

🤖 À propos de l'intelligence artificielle

L'intelligence artificielle utilisée dans certaines fonctions de TRIKA.TRAD constitue une aide à la traduction et à la compréhension du langage.

Cependant, l'IA possède encore des limites importantes concernant le lingala.

Elle peut notamment avoir des difficultés avec :

certaines expressions locales ;
les proverbes ;
les expressions familières ;
les mots ayant plusieurs significations ;
les variations régionales du lingala ;
certaines formulations utilisées dans la vie quotidienne ;
les références culturelles.

Une traduction générée par l'IA peut donc être pertinente dans certains cas, mais elle ne doit pas être considérée comme absolument parfaite.

TRIKA.TRAD est ainsi conçue comme un outil d'assistance et non comme un remplacement de la compréhension humaine de la langue.

🌐 Traduction vers et depuis l'anglais

Les traductions impliquant l'anglais nécessitent actuellement une connexion Internet lorsqu'elles utilisent les services de traduction en ligne.

Par conséquent :

Français ↔ Anglais et certaines traductions Lingala ↔ Anglais peuvent nécessiter Internet.

Sans connexion Internet, ces fonctions peuvent être limitées ou indisponibles selon le type de traduction demandé.

Les fonctionnalités basées sur les données intégrées directement dans l'application peuvent, quant à elles, fonctionner hors connexion.

🔌 Utilisation avec ou sans Internet

TRIKA.TRAD possède donc deux types de fonctionnement :

📡 Avec Internet

L'application peut accéder à des services en ligne afin d'obtenir des possibilités de traduction supplémentaires et d'utiliser certaines fonctions liées à l'intelligence artificielle.

📵 Sans Internet

Certaines traductions disponibles dans la base de données intégrée peuvent continuer à fonctionner localement.

Important : toutes les fonctionnalités de l'application ne sont pas disponibles hors connexion.

⚠️ Limites et recommandations

TRIKA.TRAD est un projet en évolution. La base linguistique du lingala continue d'être enrichie afin d'améliorer progressivement la qualité des résultats.

Pour les traductions importantes, officielles, administratives, juridiques, médicales ou professionnelles, il est recommandé de vérifier le résultat auprès d'un locuteur compétent ou d'un professionnel de la langue.

La qualité d'une traduction dépend notamment du contexte fourni, des données disponibles et, pour certaines fonctions, de la qualité de la connexion Internet.

🚀 Une application en évolution

TRIKA.TRAD est un projet qui a vocation à évoluer avec le temps.

De nouvelles fonctionnalités, de nouveaux mots, de nouvelles expressions et de nouvelles améliorations pourront être ajoutés afin de rendre l'application plus performante.

L'objectif à long terme est de contribuer à la création d'un écosystème numérique capable de mieux prendre en charge le lingala, tout en facilitant les échanges avec le français et d'autres langues
"""
        )

        layout.add_widget(self.texte)

        retour = bouton_arrondi("⬅ Retour aux paramètres", (0.32, 0.16, 0.45, 1), 55)
        retour.bind(on_press=lambda x: setattr(self.manager, "current", "parametres"))

        layout.add_widget(retour)

        self.add_widget(layout)
class HistoriqueScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12)
            
        )

        # ==================================================
        # TITRE
        # ==================================================

        layout.add_widget(
            Label(
                text="📜 HISTORIQUE",
                font_size=dp(25),
                bold=True,
                color=VIOLET_TRIKA,
                size_hint_y=None,
                height=dp(55)
            )
        )

        # ==================================================
        # ZONE HISTORIQUE
        # ==================================================
        self.historique_box = TextInput(
            text="",
            readonly=True,
            multiline=True,
            font_size=dp(14),
            padding=[dp(14), dp(14)],
            foreground_color=(0, 0, 0, 1),
            background_color=(0.24,0.10,0.34,1),
            cursor_color=(0.32, 0.16, 0.45, 1)
        )
        
    
           
        champ_style(self.historique_box)

        layout.add_widget(
            self.historique_box
        )

        # ==================================================
        # BOUTONS
        # ==================================================

        boutons = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(55)
        )

        btn_actualiser = bouton_arrondi(
            "🔄 Actualiser",
            VIOLET_TRIKA,
            52
        )

        btn_effacer = bouton_arrondi(
            "🗑️ Effacer",
            VIOLET_TRIKA,
            52
        )

        btn_actualiser.bind(
            on_press=self.afficher_historique
        )

        btn_effacer.bind(
            on_press=self.effacer_historique
        )

        boutons.add_widget(
            btn_actualiser
        )

        boutons.add_widget(
            btn_effacer
        )

        layout.add_widget(
            boutons
        )

        # ==================================================
        # RETOUR
        # ==================================================

        retour = bouton_arrondi(
            "⬅ Retour aux paramètres",
            VIOLET_TRIKA,
            52
        )

        retour.bind(
            on_press=lambda x: setattr(
                self.manager,
                "current",
                "parametres"
            )
        )

        layout.add_widget(
            retour
        )

        self.add_widget(
            layout
        )

    # ==================================================
    # CHARGEMENT AUTOMATIQUE
    # ==================================================

    def on_pre_enter(self, *args):

        self.afficher_historique(None)

    # ==================================================
    # AFFICHER HISTORIQUE
    # ==================================================

    def afficher_historique(self, instance):

        try:

            donnees = recuperer_historique()

            if not donnees:

                self.historique_box.text = (
                    "📜 HISTORIQUE\n\n"
                    "Aucune traduction enregistrée."
                )

                return

            texte = (
                "📜 HISTORIQUE DES TRADUCTIONS\n\n"
            )

            for entree, traduction, source, destination, date in donnees:

                texte += (
                    f"{source} → {destination}\n"
                    f"👤 {entree}\n"
                    f"➡️ {traduction}\n"
                    f"🕒 {date}\n"
                    "────────────────────\n\n"
                )

            self.historique_box.text = texte

        except Exception as e:

            self.historique_box.text = (
                "❌ Erreur lors du chargement de l'historique.\n\n"
                f"{e}"
            )

    # ==================================================
    # EFFACER HISTORIQUE
    # ==================================================

    def effacer_historique(self, instance):

        try:

            supprimer_historique()

            self.historique_box.text = (
                "🗑️ HISTORIQUE RÉINITIALISÉ\n\n"
                "Toutes les traductions ont été supprimées."
            )

        except Exception as e:

            self.historique_box.text = (
                "❌ Impossible d'effacer l'historique.\n\n"
                f"{e}"
            )
class TrikaTradApp(App):
    def build(self):
        self.title = "TRIKA.TRAD"
        gestionnaire = ScreenManager()
        gestionnaire.add_widget(AccueilScreen(name="accueil"))
        gestionnaire.add_widget(TraducteurScreen(name="traducteur"))
        gestionnaire.add_widget(QuizScreen(name="quiz"))
        gestionnaire.add_widget(IAScreen(name="ia"))
        gestionnaire.add_widget(ParametresScreen(name="parametres"))
        gestionnaire.add_widget(ApparenceScreen(name="apparence"))
        gestionnaire.add_widget(HistoriqueScreen(name="historique"))
        gestionnaire.add_widget(AproposScreen(name="apropos"))
        return gestionnaire

if __name__ == "__main__":
    TrikaTradApp().run()

# Fichiers visuels à placer à côté du script Android :
# logo.png       -> logo TRIKA.TRAD
# congo.png      -> drapeau du Congo
# presentation.mp4 -> vidéo de présentation affichée sur l'accueil