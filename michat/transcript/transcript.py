import speech_recognition as sr

# from .transcriber import VoiceTranscriber
from .transcriber import AudioTranscriber


def main():
    ts = AudioTranscriber()
    ts.listen()
