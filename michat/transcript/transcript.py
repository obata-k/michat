import speech_recognition as sr

# from .transcriber import VoiceTranscriber
from .transcriber import AudioTranscriber


def main():
    # ts = VoiceTranscriber(sr.Recognizer())
    ts = AudioTranscriber(sr.Recognizer())
    ts.listen()
