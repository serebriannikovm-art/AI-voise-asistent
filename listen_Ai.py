import os
import json
import threading

import vosk
import pyaudio

from openai import OpenAI

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from jnius import autoclass

Window.size = (500, 900)

# =========================================
# НАСТРОЙКИ
# =========================================
API_KEY = ""
MODEL = ""

# =========================================
# ANDROID TTS
# =========================================
def speak_android(text):
    try:
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
        Locale = autoclass('java.util.Locale')

        activity = PythonActivity.mActivity

        tts = TextToSpeech(activity, None)

        tts.setLanguage(Locale("ru", "RU"))

        tts.speak(
            text,
            TextToSpeech.QUEUE_FLUSH,
            None,
            None
        )

    except Exception as e:
        print("TTS ERROR:", e)

# =========================================
# ПОТОК РАСПОЗНАВАНИЯ РЕЧИ
# =========================================
class SpeechThread(threading.Thread):

    def __init__(self, app_screen):
        super().__init__(daemon=True)

        self.app_screen = app_screen

        self.running = True

        self.recording = False

        self.current_text = ""

        if not os.path.exists("vosk-model-small-ru-0.22"):
            print("❌ Модель Vosk не найдена")
            self.running = False
            return

        self.model = vosk.Model("vosk-model-small-ru-0.22")

        self.rec = vosk.KaldiRecognizer(
            self.model,
            16000
        )

    # =========================================
    # RUN
    # =========================================
    def run(self):

        p = pyaudio.PyAudio()

        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )

        while self.running:

            data = stream.read(
                4000,
                exception_on_overflow=False
            )

            if self.rec.AcceptWaveform(data):

                result = json.loads(self.rec.Result())

                text = result.get("text", "").lower()

                if text:
                    Clock.schedule_once(
                        lambda dt, t=text: self.process_text(t)
                    )

        stream.stop_stream()
        stream.close()
        p.terminate()

    # =========================================
    # ОБРАБОТКА КОМАНД
    # =========================================
    def process_text(self, text):

        print("УСЛЫШАНО:", text)

        # ===== НАЧАЛО =====
        if text == "начало":

            self.recording = True

            self.current_text = ""

            self.app_screen.command_label.text = \
                "[b][color=ffd000]Команда:[/color] начало[/b]"

            return

        # ===== КОНЕЦ =====
        if text == "конец":

            self.recording = False

            self.app_screen.command_label.text = \
                "[b][color=ffd000]Команда:[/color] конец[/b]"

            return

        # ===== ОЧИСТКА =====
        if text == "очистка":

            self.current_text = ""

            self.app_screen.text_label.text = ""

            self.app_screen.command_label.text = \
                "[b][color=ffd000]Команда:[/color] очистка[/b]"

            return

        # ===== ОТПРАВИТЬ =====
        if text == "отправить":

            self.app_screen.command_label.text = \
                "[b][color=ffd000]Команда:[/color] отправить[/b]"

            if self.current_text.strip():

                threading.Thread(
                    target=self.send_ai,
                    args=(self.current_text,),
                    daemon=True
                ).start()

            return

        # ===== ЗАПИСЬ =====
        if self.recording:

            self.current_text += " " + text

            self.app_screen.text_label.text = self.current_text

    # =========================================
    # ОТПРАВКА В AI
    # =========================================
    def send_ai(self, text):

        global API_KEY
        global MODEL

        if not API_KEY or not MODEL:

            Clock.schedule_once(
                lambda dt: self.app_screen.update_ai(
                    "Укажи API ключ и модель"
                )
            )

            return

        try:

            client = OpenAI(
                api_key=API_KEY,
                base_url="https://api.proxyapi.ru/openrouter/v1"
            )

            response = client.chat.completions.create(

                model=MODEL.strip(),

                messages=[
                    {
                        "role": "user",
                        "content": text + " дай только ответ без звёздочек"
                    }
                ]
            )

            answer = response.choices[0].message.content

            # ===== ВЫВОД ТЕКСТА =====
            Clock.schedule_once(
                lambda dt: self.app_screen.update_ai(answer)
            )

            # ===== ОЗВУЧКА =====
            threading.Thread(
                target=speak_android,
                args=(answer,),
                daemon=True
            ).start()

        except Exception as e:

            Clock.schedule_once(
                lambda dt: self.app_screen.update_ai(
                    f"Ошибка: {str(e)}"
                )
            )

# =========================================
# ГЛАВНЫЙ ЭКРАН
# =========================================
class MainScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(
            orientation='vertical',
            padding=25,
            spacing=20
        )

        # =========================================
        # ФОН
        # =========================================
        with root.canvas.before:
            Color(0.26, 0.26, 0.26, 1)

            self.rect = Rectangle(
                size=root.size,
                pos=root.pos
            )

        root.bind(
            size=self.update_rect,
            pos=self.update_rect
        )

        # =========================================
        # TOP
        # =========================================
        top = BoxLayout(
            size_hint_y=None,
            height=80
        )

        top.add_widget(Label())

        menu_btn = Button(
            text="",
            size_hint=(None, None),
            size=(95, 95),
            background_normal="menu.png",
            background_down="menu.png",
            border=(0, 0, 0, 0),
            background_color=(1, 1, 1, 1)
        )

        menu_btn.bind(on_press=self.open_settings)

        top.add_widget(menu_btn)

        root.add_widget(top)

        # =========================================
        # МИКРОФОН
        # =========================================
        self.mic = Image(
            source="mic_off.png",
            size_hint=(1, None),
            height=300,
            allow_stretch=True,
            keep_ratio=True
        )

        root.add_widget(self.mic)

        # =========================================
        # СТАТУС
        # =========================================
        self.status_label = Label(
            text="[b][color=ffd000]Статус:[/color] ВЫКЛЮЧЕН[/b]",
            markup=True,
            font_size=28,
            size_hint_y=None,
            height=60
        )

        root.add_widget(self.status_label)

        # =========================================
        # КОМАНДА
        # =========================================
        self.command_label = Label(
            text="[b][color=ffd000]Команда:[/color] -[/b]",
            markup=True,
            font_size=24,
            size_hint_y=None,
            height=50
        )

        root.add_widget(self.command_label)

        # =========================================
        # ПОДСКАЗКА
        # =========================================
        helper = Label(
            text="[color=ffd000](начало, конец, отправить, очистка)[/color]",
            markup=True,
            font_size=18,
            size_hint_y=None,
            height=35
        )

        root.add_widget(helper)

        # =========================================
        # ТЕКСТ
        # =========================================
        title1 = Label(
            text="[b][color=ffd000]Текст:[/color][/b]",
            markup=True,
            font_size=38,
            size_hint_y=None,
            height=70,
            halign="left"
        )

        title1.bind(size=title1.setter('text_size'))

        root.add_widget(title1)

        text_box = BoxLayout(
            size_hint_y=None,
            height=240,
            padding=20
        )

        with text_box.canvas.before:
            Color(0.85, 0.85, 0.85, 1)

            self.text_rect = Rectangle(
                size=text_box.size,
                pos=text_box.pos
            )

        text_box.bind(
            size=self.update_text_rect,
            pos=self.update_text_rect
        )

        scroll1 = ScrollView()

        self.text_label = Label(
            text="",
            color=(0, 0, 0, 1),
            font_size=24,
            size_hint_y=None,
            valign='top'
        )

        self.text_label.bind(
            texture_size=self.update_text_height
        )

        scroll1.add_widget(self.text_label)

        text_box.add_widget(scroll1)

        root.add_widget(text_box)

        # =========================================
        # AI
        # =========================================
        title2 = Label(
            text="[b][color=ffd000]Ответ AI:[/color][/b]",
            markup=True,
            font_size=38,
            size_hint_y=None,
            height=70,
            halign="left"
        )

        title2.bind(size=title2.setter('text_size'))

        root.add_widget(title2)

        ai_box = BoxLayout(
            size_hint_y=None,
            height=240,
            padding=20
        )

        with ai_box.canvas.before:
            Color(0.85, 0.85, 0.85, 1)

            self.ai_rect = Rectangle(
                size=ai_box.size,
                pos=ai_box.pos
            )

        ai_box.bind(
            size=self.update_ai_rect,
            pos=self.update_ai_rect
        )

        scroll2 = ScrollView()

        self.ai_label = Label(
            text="",
            color=(0, 0, 0, 1),
            font_size=24,
            size_hint_y=None,
            valign='top'
        )

        self.ai_label.bind(
            texture_size=self.update_ai_height
        )

        scroll2.add_widget(self.ai_label)

        ai_box.add_widget(scroll2)

        root.add_widget(ai_box)

        # =========================================
        # КНОПКА
        # =========================================
        self.toggle_btn = Button(
            text="ВКЛ / ВЫКЛ",
            size_hint_y=None,
            height=70,
            font_size=24,
            background_color=(0.35, 0.35, 0.35, 1)
        )

        self.toggle_btn.bind(on_press=self.toggle)

        root.add_widget(self.toggle_btn)

        self.add_widget(root)

        self.thread = None

    # =========================================
    # UPDATE RECT
    # =========================================
    def update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def update_text_rect(self, instance, value):
        self.text_rect.size = instance.size
        self.text_rect.pos = instance.pos

    def update_ai_rect(self, instance, value):
        self.ai_rect.size = instance.size
        self.ai_rect.pos = instance.pos

    def update_text_height(self, instance, value):
        instance.height = value[1]
        instance.text_size = (instance.width - 20, None)

    def update_ai_height(self, instance, value):
        instance.height = value[1]
        instance.text_size = (instance.width - 20, None)

    # =========================================
    # SETTINGS
    # =========================================
    def open_settings(self, instance):
        self.manager.current = "settings"

    # =========================================
    # TOGGLE
    # =========================================
    def toggle(self, instance):

        if not self.thread:

            self.thread = SpeechThread(self)

            self.thread.start()

            self.status_label.text = \
                "[b][color=ffd000]Статус:[/color] ВКЛЮЧЕН[/b]"

            self.mic.source = "mic_on.png"

        else:

            self.thread.running = False

            self.thread = None

            self.status_label.text = \
                "[b][color=ffd000]Статус:[/color] ВЫКЛЮЧЕН[/b]"

            self.mic.source = "mic_off.png"

    # =========================================
    # UPDATE AI
    # =========================================
    def update_ai(self, text):

        self.ai_label.text = text

# =========================================
# НАСТРОЙКИ
# =========================================
class SettingsScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(
            orientation='vertical',
            padding=30,
            spacing=30
        )

        with root.canvas.before:
            Color(0.26, 0.26, 0.26, 1)

            self.rect = Rectangle(
                size=root.size,
                pos=root.pos
            )

        root.bind(
            size=self.update_rect,
            pos=self.update_rect
        )

        # =========================================
        # TOP
        # =========================================
        top = BoxLayout(
            size_hint_y=None,
            height=100
        )

        title = Label(
            text="[b][color=ffd000]AI API:[/color][/b]",
            markup=True,
            font_size=42
        )

        top.add_widget(title)

        close_btn = Button(
            text="",
            size_hint=(None, None),
            size=(95, 95),
            background_normal="close.png",
            background_down="close.png",
            border=(0, 0, 0, 0),
            background_color=(1, 1, 1, 1)
        )

        close_btn.bind(on_press=self.close)

        top.add_widget(close_btn)

        root.add_widget(top)

        # =========================================
        # MODEL
        # =========================================
        model_title = Label(
            text="[b][color=ffd000]Model AI:[/color][/b]",
            markup=True,
            font_size=34,
            size_hint_y=None,
            height=60,
            halign="left"
        )

        model_title.bind(size=model_title.setter('text_size'))

        root.add_widget(model_title)

        self.login_input = TextInput(
            multiline=False,
            size_hint_y=None,
            height=90,
            font_size=26,
            background_color=(0.85, 0.85, 0.85, 1),
            foreground_color=(0, 0, 0, 1),
            padding=[25, 25]
        )

        root.add_widget(self.login_input)

        # =========================================
        # API KEY
        # =========================================
        pass_title = Label(
            text="[b][color=ffd000]Key AI:[/color][/b]",
            markup=True,
            font_size=34,
            size_hint_y=None,
            height=60,
            halign="left"
        )

        pass_title.bind(size=pass_title.setter('text_size'))

        root.add_widget(pass_title)

        self.password_input = TextInput(
            multiline=False,
            password=True,
            size_hint_y=None,
            height=90,
            font_size=26,
            background_color=(0.85, 0.85, 0.85, 1),
            foreground_color=(0, 0, 0, 1),
            padding=[25, 25]
        )

        root.add_widget(self.password_input)

        # =========================================
        # SAVE
        # =========================================
        save_btn = Button(
            text="Сохранить",
            size_hint_y=None,
            height=90,
            font_size=34,
            background_color=(0.85, 0.85, 0.85, 1),
            color=(0, 0, 0, 1)
        )

        save_btn.bind(on_press=self.save)

        root.add_widget(Label())

        root.add_widget(save_btn)

        self.add_widget(root)

    def update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def close(self, instance):
        self.manager.current = "main"

    def save(self, instance):

        global API_KEY
        global MODEL

        MODEL = self.login_input.text.strip()

        API_KEY = self.password_input.text.strip()

        self.manager.current = "main"

# =========================================
# APP
# =========================================
class MyApp(App):

    def build(self):

        sm = ScreenManager()

        sm.add_widget(MainScreen(name="main"))

        sm.add_widget(SettingsScreen(name="settings"))

        return sm

# =========================================
# START
# =========================================
if __name__ == "__main__":
    MyApp().run()