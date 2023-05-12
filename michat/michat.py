from argparse import ArgumentParser
from pathlib import Path

import speech_recognition as sr

from lib.speak import Audio, ChatGPT, setup_log
from lib.transcript import VoiceTranscriber


def main():
    progname = Path(__file__).name
    parser = ArgumentParser(description=progname)
    parser.add_argument(
        "--file", help="message to submit to ChatGPT", default="input.txt"
    )
    parser.add_argument(
        "--file-system", help="system message for ChatGPT", default="system.txt"
    )
    parser.add_argument(
        "-t", "--max-tokens", help="Maximum tokens of ChatGPT response", default=256
    )
    parser.add_argument(
        "-s", "--speaker-id", help="Speaker ID for the VOICEVOX model", default=3
    )
    parser.add_argument("-o", "--output", help="wav output", default="output.wav")
    parser.add_argument("-L", "--log-file", help="log output file", default="stdout")
    parser.add_argument("-l", "--log-level", help="logger level", default="INFO")
    args = parser.parse_args()

    logger = setup_log(log_file=args.log_file, log_level=args.log_level)

    speaker_id = args.speaker_id
    max_token_size = args.max_tokens
    system_file = Path(args.file_system)
    output = Path(args.output)

    ts = VoiceTranscriber()
    audio = Audio(speaker_id)
    chat = ChatGPT(max_token_size)
    system_text = open(system_file, "r").read()

    logger.info("Listening...")
    for user_text in ts.listen():
        if isinstance(user_text, sr.UnknownValueError):
            logger.error("わかりません...")
        elif isinstance(user_text, sr.RequestError):
            logger.error("ごめんなさい！リクエストに失敗しました...")
        elif isinstance(user_text, Exception):
            logger.error(user_text)
            raise user_text

        gen_text = chat.generate(system_text, user_text)
        logger.info(gen_text)

        audio.transform(gen_text)
        audio.save_wav(output)
        audio.play(output)
