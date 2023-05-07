import io
import logging
import base64
from PIL import Image
import time
import numpy as np
import queue
from pathlib import Path
from streamlit_chat import message
from streamlit.logger import get_logger

import pydub
import streamlit as st
from lib.speak import ChatGPTWithEmotion, ChatGPTFeature, Audio, system_text
from lib.transcript import AudioTranscriber
from streamlit_webrtc import WebRtcMode, webrtc_streamer


# stremlit status
AUDIO_BUFFER = "audio_buffer"
BOT_MESSAGES = "bot_messages"
USR_MESSAGES = "usr_messages"
READ_INDEX = "read_index"
SPEAKER_ID = "speaker_id"
MODE = "chat_mode"
EMOTIONS = "emotions"
FEATURE = "feature"
HISTORY = "history"
VISIBILITY = "visibility"

# chatgpt
OUTPUT = Path("output.wav")


class WebRTCRecorder:
    def __init__(self):
        if AUDIO_BUFFER not in st.session_state:
            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()
        if BOT_MESSAGES not in st.session_state:
            st.session_state[BOT_MESSAGES] = []
        if USR_MESSAGES not in st.session_state:
            st.session_state[USR_MESSAGES] = []
        if EMOTIONS not in st.session_state:
            st.session_state[EMOTIONS] = None
        if SPEAKER_ID not in st.session_state:
            st.session_state[SPEAKER_ID] = 3
        if MODE not in st.session_state:
            st.session_state[MODE] = "chat"  # 'chat' or 'image'
        if FEATURE not in st.session_state:
            st.session_state[FEATURE] = ChatGPTFeature.ZUNDAMON
        if HISTORY not in st.session_state:
            st.session_state[HISTORY] = []
        if READ_INDEX not in st.session_state:
            st.session_state[READ_INDEX] = -1
        if VISIBILITY not in st.session_state:
            st.session_state.visibility = "visible"
            st.session_state.disabled = False

        self.max_token_size = 512  # const

        self.webrtc_ctx = webrtc_streamer(
            key="michat",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            },
            media_stream_constraints={"video": False, "audio": True},
            audio_receiver_size=1024,
        )

    def listen(self):
        if not self.webrtc_ctx.state.playing:
            return

        self.status_box = st.empty()

        while True:
            print("listen")
            if self.webrtc_ctx.audio_receiver:
                try:
                    audio_frames = self.webrtc_ctx.audio_receiver.get_frames(
                        timeout=0.5
                    )
                except queue.Empty:
                    self.status_box.warning("No frame arrived.")
                    continue

                self.status_box.info("何か聞いてね！")

                sound_chunk = pydub.AudioSegment.empty()
                for audio_frame in audio_frames:
                    sound = pydub.AudioSegment(
                        data=audio_frame.to_ndarray().tobytes(),
                        sample_width=audio_frame.format.bytes,
                        frame_rate=audio_frame.sample_rate,
                        channels=len(audio_frame.layout.channels),
                    )
                    sound_chunk += sound

                if len(sound_chunk) > 0:
                    st.session_state[AUDIO_BUFFER] += sound_chunk
            else:
                break

    def __background_play(self, file):
        audio_placeholder = st.empty()
        with open(file, "rb") as ow:
            wav_content = ow.read()
        audio_str = "data:audio/ogg;base64,%s" % (
            base64.b64encode(wav_content).decode()
        )
        audio_html = (
            """
            <audio autoplay=True>
            <source src="%s" type="audio/ogg" autoplay=True>
            Your browser does not support the audio element.
            </audio>
        """
            % audio_str
        )
        audio_placeholder.empty()
        audio_placeholder.markdown(audio_html, unsafe_allow_html=True)

    def to_text(self):
        audio_buffer = st.session_state[AUDIO_BUFFER]
        ts = AudioTranscriber()

        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            try:
                wav_bytes = io.BytesIO()
                audio_buffer.export(wav_bytes, format="wav")
                text = ts.listen(wav_bytes)
                st.session_state[USR_MESSAGES].append(text)
            except Exception as e:
                st.error(f"Error while transcripting: {e}")

            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()
            return text

    def generate_and_play(self):
        if self.webrtc_ctx.state.playing or len(st.session_state[USR_MESSAGES]) == 0:
            return (None, None)
        if st.session_state[READ_INDEX] == len(st.session_state[BOT_MESSAGES]):
            return (st.session_state[BOT_MESSAGES][-1], st.session_state[EMOTIONS])
        text = st.session_state[USR_MESSAGES][-1]
        chat = ChatGPTWithEmotion(self.max_token_size)
        speaker = Audio(self.speaker_id)
        history = st.session_state[HISTORY][-6:]  # 最新6件

        try:
            st.session_state.disabled = True
            system = system_text(self.feature)
            generated, history, emotions = chat.generate(system, text, history)
            speaker.transform(generated)
            speaker.save_wav(OUTPUT)
            self.__background_play(OUTPUT)
            st.session_state[BOT_MESSAGES].append(generated)
            st.session_state[READ_INDEX] = len(st.session_state[BOT_MESSAGES])
        except Exception as e:
            st.error(f"Error while request and play: {e}")
        finally:
            st.session_state.disabled = False
        st.session_state[EMOTIONS] = emotions
        return (generated, emotions)

    def chat_view(self):
        if len(st.session_state[USR_MESSAGES]) == 0:
            return

        container = st.container()
        if st.session_state[BOT_MESSAGES]:
            with container:
                for i in range(len(st.session_state[BOT_MESSAGES]) - 1, -1, -1):
                    message(st.session_state[BOT_MESSAGES][i], key=str(i))
                    message(
                        st.session_state[USR_MESSAGES][i],
                        is_user=True,
                        key=str(i) + "_usr",
                    )

    def __max_emotion(self, emotions):
        if emotions is None:
            return ("通常", -1)
        return max(emotions.items(), key=lambda x: x[1])

    def get_image(self, emotions=None):
        images = {
            "通常": "./images/zunda-normal.png",
            "喜び": "./images/zunda-joy.png",
            "楽しさ": "./images/zunda-fun.png",
            "怒り": "./images/zunda-anger.png",
            "悲しみ": "./images/zunda-sad.png",
            "自信": "./images/zunda-confidence.png",
            "恐怖": "./images/zunda-fear.png",
            "困惑": "./images/zunda-confused.png",
        }
        max_emotion, value = self.__max_emotion(emotions)
        if value == 0:
            max_emotion = "通常"
        return Image.open(images[max_emotion])

    def image_view(self, text, emotions):
        image = self.get_image(emotions)
        col1, col2, col3 = st.columns([1, 6, 1])
        with col1:
            st.write("")
        with col2:
            st.image(image, caption=text, width=500)
        with col3:
            st.write("")


def voice_options():
    speakers = {
        "四国めたん（あまあま）": 0,
        "四国めたん（ノーマル）": 2,
        "四国めたん（ツンツン）": 6,
        "四国めたん（セクシー）": 4,
        "ずんだもん（ノーマル）": 3,
        "ずんだもん（あまあま）": 1,
        "ずんだもん（ツンツン）": 7,
        "ずんだもん（セクシー）": 5,
        "春日部つむぎ（ノーマル）": 8,
        "雨晴はう（ノーマル）": 10,
        "玄野武宏（ノーマル）": 11,
        "白上虎太郎（ノーマル）": 12,
        "青山龍星（ノーマル）": 13,
        "冥鳴ひまり（ノーマル）": 14,
        "九州そら（あまあま）": 15,
        "九州そら（ツンツン）": 18,
        "九州そら（セクシー）": 17,
        "九州そら（ささやき）": 19,
    }
    option = st.selectbox(
        "音声",
        (list(speakers.keys())),
        index=4,
        label_visibility=st.session_state.visibility,
        disabled=st.session_state.disabled,
    )
    st.session_state[SPEAKER_ID] = speakers[option]
    return st.session_state[SPEAKER_ID]


def mode_options():
    st.session_state[MODE] = st.radio(
        "モード選択",
        ("image", "chat"),
        label_visibility=st.session_state.visibility,
        disabled=st.session_state.disabled,
    )
    return st.session_state[MODE]


def feautre_option():
    feature = st.selectbox(
        "口調",
        (ChatGPTFeature.get_values()),
        label_visibility=st.session_state.visibility,
        disabled=st.session_state.disabled,
    )
    st.session_state[FEATURE] = ChatGPTFeature.value_of(feature)
    return st.session_state[FEATURE]


def app():
    image = Image.open("images/zunda-icon.png")
    st.set_page_config(page_title="michat - DEMO", page_icon=image)
    st.title("michat")

    logger = get_logger(__name__)
    logger.setLevel(logging.INFO)

    webrtc = WebRTCRecorder()

    with st.sidebar:
        mode = mode_options()
        voice_options()
        feautre_option()

    webrtc.listen()  # busy loop here
    webrtc.to_text()
    generated, emotions = webrtc.generate_and_play()
    print("generated", generated)
    print(READ_INDEX, st.session_state[READ_INDEX])
    print(USR_MESSAGES, st.session_state[USR_MESSAGES])
    print(BOT_MESSAGES, st.session_state[BOT_MESSAGES])

    if mode == "chat":
        webrtc.chat_view()
    else:
        webrtc.image_view(generated, emotions)


if __name__ == "__main__":
    app()
