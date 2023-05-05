import io
from abc import ABCMeta, abstractmethod
from pathlib import Path

import speech_recognition as sr


class Transcriber(metaclass=ABCMeta):
    def __init__(self):
        self.recognizer = sr.Recognizer()
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
    def __init__(self):
        super().__init__()

    @classmethod
    def default_input(cls):
        return sr.Microphone()

    def listen(self, _from=None):
        if _from is None:
            _from = self.default_input()

        with _from as source:
            self.recognizer.adjust_for_ambient_noise(source)

            yield "Listening..."
            try:
                while True:
                    try:
                        audio = self.recognizer.listen(source)
                        text = self.recognizer.recognize_google(audio, language="ja-JP")
                        yield text
                    except sr.UnknownValueError:
                        yield "よくわかりません..."
                    except sr.RequestError:
                        yield "ごめんなさい！リクエストに失敗しました..."

            except KeyboardInterrupt:
                yield "ばいばい、またね"


class AudioTranscriber(Transcriber):
    def __init__(self, wav=None):
        self.wav = wav
        self.audio_file = None
        super().__init__()

    @classmethod
    def default_file(cls):
        return "output.wav"

    @classmethod
    def default_input(cls):
        file = cls.default_file()
        return sr.AudioFile(file)

    def listen(self, _from=None):
        try:
            if _from is None:
                self.audio_file = self.default_input()
            elif isinstance(_from, io.BytesIO):
                self.audio_file = sr.AudioFile(_from)

            if self.audio_file is None:
                self.audio_file = sr.AudioFile(self.wav)

            with self.audio_file as source:
                audio = self.recognizer.record(source)

            text = self.recognizer.recognize_google(audio, language="ja-JP")
            yield text
        except sr.UnknownValueError:
            yield "よくわかりません..."
        except sr.RequestError:
            yield "ごめんなさい！リクエストに失敗しました..."
