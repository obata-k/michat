import speech_recognition as sr
from abc import ABCMeta, abstractmethod
from pathlib import Path


class Transcriber(metaclass=ABCMeta):
    def __init__(self, input=None, logger=None):
        self.recognizer = sr.Recognizer()
        self.input = input
        self.logger = logger

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, v):
        self._input = v

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, lg):
        self._logger = lg

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

            try:
                while True:
                    try:
                        audio = self.recognizer.listen(source)
                        text = self.recognizer.recognize_google(audio, language="ja-JP")
                        yield text
                    except Exception as e:
                        yield e

            except KeyboardInterrupt:
                yield "ばいばい、またね"
                return


class AudioTranscriber(Transcriber):
    def __init__(self, wav=None):
        self.recognizer = sr.Recognizer()
        self.wav = wav

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
            self.wav = self.default_file()
        if not Path(self.wav).exists():
            raise FileNotFoundError
        with _from as source:
            audio = self.recognizer.record(source)

        text = self.recognizer.recognize_google(audio, language="ja-JP")
        return text
