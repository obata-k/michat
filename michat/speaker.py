from lib.speak import setup_log, Audio, ChatGPT
from argparse import ArgumentParser
from pathlib import Path


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
    user_file = Path(args.file)
    output = Path(args.output)

    system_text = open(system_file, "r").read()
    user_text = open(user_file, "r").read()

    # ChatGPTで文章の生成
    chat = ChatGPT(max_token_size)
    gen_text = chat.generate(system_text, user_text)
    logger.info(gen_text)

    # 音声出力
    audio = Audio(speaker_id)
    audio.transform(gen_text)
    audio.save_wav(output)
    audio.play(output)


if __name__ == "__main__":
    main()
