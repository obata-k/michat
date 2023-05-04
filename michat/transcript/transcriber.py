import speech_recognition as sr
from abc import ABCMeta, abstractmethod


class Transcriber(metaclass=ABCMeta):
    def __init__(self, rc):
        self.recognizer = rc
        self.input = None

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, v):
        self._input = v

    @abstractmethod
    def listen(self, _from):
        pass


class VoiceTranscriber(Transcriber):
    @classmethod
    def default_input(cls):
        return sr.Microphone()

    def listen(self, _from=None):
        if _from is None:
            _from = self.default_input()
        with _from as source:
            self.recognizer.adjust_for_ambient_noise(source)

            print("Listening...")
            try:
                while True:
                    try:
                        audio = self.recognizer.listen(source)
                        text = self.recognizer.recognize_google(audio, language="ja-JP")
                        print(text)
                    except sr.UnknownValueError:
                        print("よくわかりません...")
                    except sr.RequestError:
                        print("ごめんなさい！リクエストに失敗しました...")

            except KeyboardInterrupt:
                print("ばいばい、またね")


class AudioTranscriber(Transcriber):
    def __init__(self, rc, wav=None):
        self.wav = wav
        self.recognizer = rc

    @classmethod
    def default_file(cls):
        return "output.wav"

    @classmethod
    def default_input(cls):
        file = cls.default_file()
        return sr.AudioFile(file)

    def listen(self, _from=None):
        if _from is None:
            _from = self.default_input()
        with _from as source:
            audio = self.recognizer.record(source)

        text = self.recognizer.recognize_google(audio, language="ja-JP")
        print(text)
