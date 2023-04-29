import os
from argparse import ArgumentParser
from pathlib import Path

import openai
import voicevox_core
from dotenv import load_dotenv
from playsound import playsound
from voicevox_core import AccelerationMode, AudioQuery, VoicevoxCore

open_jtalk_dict_dir = './open_jtalk_dic_utf_8-1.11'
acceleration_mode = AccelerationMode.AUTO


class ChatGPT:
    def __init__(self, max_token_size):
        self.__max_token_size = max_token_size
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
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
            }
        ]

        # GPT-3でテキストを生成する
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=self.max_token_size,
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
            acceleration_mode=acceleration_mode,
            open_jtalk_dict_dir=open_jtalk_dict_dir
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


def main():
    parser = ArgumentParser(description="speaker")
    parser.add_argument(
        '--file', help='message to submit to ChatGPT', default='input.txt')
    parser.add_argument(
        '--file-system', help='system message for ChatGPT',
        default='system.txt')
    parser.add_argument('-t', '--max-tokens',
                        help='Maximum tokens of ChatGPT response',
                        default=1024)
    parser.add_argument('-s', '--speaker-id',
                        help='Speaker ID for the VOICEVOX model', default=3)
    parser.add_argument('-o', '--output', help='wav output',
                        default='output.wav')
    args = parser.parse_args()

    speaker_id = args.speaker_id
    max_token_size = args.max_tokens
    system_file = Path(args.file_system)
    user_file = Path(args.file)
    output = Path(args.output)

    system_text = open(system_file, 'r').read()
    user_text = open(user_file, 'r').read()

    # ChatGPTで文章の生成
    chat = ChatGPT(max_token_size)
    gen_text = chat.generate(system_text, user_text)
    print(gen_text)

    # 音声出力
    audio = Audio(speaker_id)
    audio.transform(gen_text)
    audio.save_wav(output)
    audio.play(output)


if __name__ == "__main__":
    main()
