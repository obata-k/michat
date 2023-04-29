import logging
import os
from argparse import ArgumentParser
from pathlib import Path

import openai
from dotenv import load_dotenv
from playsound import playsound
from voicevox_core import AccelerationMode, VoicevoxCore

open_jtalk_dict_dir = "./open_jtalk_dic_utf_8-1.11"
acceleration_mode = AccelerationMode.AUTO


class ChatGPT:
    def __init__(self, max_token_size):
        self.__max_token_size = max_token_size
        dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
        load_dotenv(dotenv_path)
        openai.api_key = os.environ.get("OPENAI_API_KEY")

    @property
    def max_token_size(self):
        return self.__max_token_size

    @max_token_size.setter
    def max_token_size(self, n):
        self.__max_token_size = n

    def generate(self, system_text, user_text):
        # system role のメッセージ
        messages = [
            {
                "role": "system",
                "content": system_text,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ]

        # GPT-3でテキストを生成する
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=int(self.max_token_size),
            n=1,
            stop=None,
            temperature=0.5,
        )

        # GPT-3の生成したテキストを取得する
        text = response.choices[0].message.content.strip()
        return text


class Audio:
    def __init__(self, speaker_id):
        self.speaker_id = speaker_id

    # voicevoxでテキストを音声に変換する
    def transform(self, text):
        self.core = VoicevoxCore(
            acceleration_mode=acceleration_mode, open_jtalk_dict_dir=open_jtalk_dict_dir
        )
        self.core.load_model(self.speaker_id)
        self.audio_query = self.core.audio_query(text, self.speaker_id)

    # 音声をファイルに保存する
    def save_wav(self, out):
        wav = self.core.synthesis(self.audio_query, self.speaker_id)
        out.write_bytes(wav)

    # 音声を再生する
    def play(self, file):
        playsound(file)


def setup_log(log_file, log_level):
    FORMAT = "%(asctime)s: [%(levelname)s] %(message)s"
    logging.basicConfig(format=FORMAT)

    level_num = getattr(logging, log_level.upper(), None)
    if not isinstance(level_num, int):
        raise ValueError("Invalid log level: %s" % log_level)
    logger = logging.getLogger(__name__)
    logger.setLevel(level_num)

    if log_file == "stdout":
        stdout_handler = logging.StreamHandler()
        logger.addHandler(stdout_handler)
    else:
        file_handler = logging.FileHandler(filename=log_file)
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger


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
