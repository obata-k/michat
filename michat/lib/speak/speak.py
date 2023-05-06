import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from enum import Enum

import openai
from dotenv import load_dotenv
from playsound import playsound
from voicevox_core import AccelerationMode, VoicevoxCore

open_jtalk_dict_dir = "./open_jtalk_dic_utf_8-1.11"
acceleration_mode = AccelerationMode.AUTO


class ChatGPTFeature(Enum):
    ZUNDAMON = "ずんだもん"
    ENE = "エネ"
    MIKU = "初音ミク"

    @classmethod
    def get_names(cls) -> list:
        return [i.name for i in cls]

    @classmethod
    def get_values(cls) -> list:
        return [i.value for i in cls]

    @classmethod
    def value_of(cls, target_value):
        for e in ChatGPTFeature:
            if e.value == target_value:
                return e
        raise ValueError("{} is not a valid feature".format(target_value))


class ChatGPT:
    def __init__(self, max_token_size):
        self.__max_token_size = max_token_size
        env_root = Path(os.getcwd())
        dotenv_path = os.path.join(env_root, ".env")
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


def system_text(feature=ChatGPTFeature.ZUNDAMON):
    if feature is ChatGPTFeature.ZUNDAMON:
        system = Path("system-zundamon.txt")
    elif feature is ChatGPTFeature.ENE:
        system = Path("system-ene.txt")
    elif feature is ChatGPTFeature.MIKU:
        system = Path("system-miku.txt")
    else:
        raise ValueError("invalid ChatGPT feature was set")

    with open(system, "r") as f:
        text = f.read()
    return text
