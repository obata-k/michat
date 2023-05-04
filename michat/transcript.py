from lib.transcript import VoiceTranscriber


def main():
    ts = VoiceTranscriber()
    for text in ts.listen():
        print(text)


if __name__ == '__main__':
    main()
