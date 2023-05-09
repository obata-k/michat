import io
import base64
import logging
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
GENERATED_INDEX = "generated_index"
READ_INDEX = "read_index"
SPEAKER_ID = "speaker_id"
MODE_INDEX = "mode_index"
EMOTIONS = "emotions"
FEATURE_INDEX = "feature_index"
HISTORY = "history"
VISIBILITY = "visibility"
RERUNED = "reruned"

# chatgpt response to wav
OUTPUT = Path("output.wav")

logger = get_logger("streamlit_webrtc")
logger.setLevel(logging.INFO)


def session_init():
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
    if MODE_INDEX not in st.session_state:
        st.session_state[MODE_INDEX] = 0
    if FEATURE_INDEX not in st.session_state:
        st.session_state[FEATURE_INDEX] = 0
    if HISTORY not in st.session_state:
        st.session_state[HISTORY] = []
    if GENERATED_INDEX not in st.session_state:
        st.session_state[GENERATED_INDEX] = None
    if READ_INDEX not in st.session_state:
        st.session_state[READ_INDEX] = None
    if RERUNED not in st.session_state:
        st.session_state[RERUNED] = False
    if VISIBILITY not in st.session_state:
        st.session_state.visibility = "visible"
        st.session_state.disabled = False


class WebRTCRecorder:
    def __init__(self):
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
        self.status_box = st.empty()

        if not self.webrtc_ctx.state.playing:
            return

        self.status_box.info("Loading...")

        while True:
            if self.webrtc_ctx.audio_receiver:
                try:
                    audio_frames = self.webrtc_ctx.audio_receiver.get_frames(timeout=1)
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

    def generate(self, feature):
        audio_buffer = st.session_state[AUDIO_BUFFER]
        ts = AudioTranscriber()
        chat = ChatGPTWithEmotion(self.max_token_size)
        history = st.session_state[HISTORY][-6:]  # 最新6件

        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            try:
                # create wev
                wav_bytes = io.BytesIO()
                audio_buffer.export(wav_bytes, format="wav")
                # transcript
                user_text = ts.listen(wav_bytes)
                st.session_state[USR_MESSAGES].append(user_text)
            except Exception as e:
                st.error(f"Error while transcripting: {e}")

            try:
                # generate text
                system = system_text(feature)
                generated, history, emotions = chat.generate(system, user_text, history)
                st.session_state[BOT_MESSAGES].append(generated)
                st.session_state[GENERATED_INDEX] = len(st.session_state[BOT_MESSAGES])
                st.session_state[READ_INDEX] = len(st.session_state[BOT_MESSAGES]) - 1
            except Exception as e:
                st.error(f"Error while generating: {e}")

            st.session_state[EMOTIONS] = emotions
            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()
            return (generated, emotions)
        else:
            return (None, None)

    def audio_play(self, speaker_id):
        if (
            len(st.session_state[BOT_MESSAGES]) == 0
            or st.session_state[READ_INDEX] is None
            or self.webrtc_ctx.state.playing
        ):
            return
        read_index = st.session_state[GENERATED_INDEX] - 1
        logger.debug("now plaing [index: {}]".format(read_index))
        text = st.session_state[BOT_MESSAGES][read_index]
        # play audio
        speaker = Audio(speaker_id)
        speaker.transform(text)
        speaker.save_wav(OUTPUT)
        self.__background_play(OUTPUT)
        st.session_state[READ_INDEX] = st.session_state[GENERATED_INDEX]


def max_emotion(emotions=None) -> str:
    if emotions is None:
        return "通常"
    return max(emotions, key=emotions.get)


@st.cache_data
def emotion_image_path(emotion: str):
    root = Path("images")
    images = {
        "通常": "zunda-normal.png",
        "喜び": "zunda-joy.png",
        "楽しさ": "zunda-fun.png",
        "怒り": "zunda-anger.png",
        "悲しみ": "zunda-sad.png",
        "自信": "zunda-confidence.png",
        "恐怖": "zunda-fear.png",
        "困惑": "zunda-confused.png",
    }
    return Image.open(root / Path(images[emotion]))


def get_image(emotions: dict):
    max_emotion_str = max_emotion(emotions)
    if (
        emotions is None
        or max_emotion_str not in emotions
        or emotions[max_emotion_str] == 0
    ):
        max_emotion_str = "通常"
    return emotion_image_path(max_emotion_str)


def chat_view():
    if len(st.session_state[USR_MESSAGES]) == 0:
        return

    container = st.container()
    if st.session_state[BOT_MESSAGES]:
        with container:
            for i in range(len(st.session_state[BOT_MESSAGES])):
                message(
                    st.session_state[USR_MESSAGES][i],
                    is_user=True,
                    key=str(i) + "_usr",
                )
                message(st.session_state[BOT_MESSAGES][i], key=str(i))


def image_view():
    emotions = st.session_state[EMOTIONS]
    gen_index = st.session_state[GENERATED_INDEX]
    logger.debug(st.session_state[BOT_MESSAGES])
    if gen_index is None:
        text = ""
    else:
        text = st.session_state[BOT_MESSAGES][gen_index - 1]

    image = get_image(emotions)
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        st.write("")
    with col2:
        st.write("")
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

    def speakers_state_update():
        st.session_state[SPEAKER_ID] = speakers[st.session_state.speakers_selectbox]

    option = st.selectbox(
        "音声",
        (list(speakers.keys())),
        key="speakers_selectbox",
        index=4,
        label_visibility=st.session_state.visibility,
        on_change=speakers_state_update,
        disabled=st.session_state.disabled,
    )
    if st.session_state != speakers[option]:
        st.session_state[SPEAKER_ID] = speakers[option]
    return st.session_state[SPEAKER_ID]


def mode_options():
    modes = ["image", "chat"]

    def mode_state_update():
        st.session_state[MODE_INDEX] = modes.index(st.session_state.mode_radio)

    view_mode = st.radio(
        "モード選択",
        modes,
        key="mode_radio",
        index=st.session_state[MODE_INDEX],
        label_visibility=st.session_state.visibility,
        on_change=mode_state_update,
        disabled=st.session_state.disabled,
    )
    st.session_state[MODE_INDEX] = modes.index(view_mode)
    return view_mode


def feautre_option():
    def feature_state_update():
        st.session_state[FEATURE_INDEX] = ChatGPTFeature.index(
            st.session_state.feature_selectbox
        )

    feature = st.selectbox(
        "口調",
        (ChatGPTFeature.get_values()),
        key="feature_selectbox",
        index=st.session_state[FEATURE_INDEX],
        label_visibility=st.session_state.visibility,
        on_change=feature_state_update,
        disabled=st.session_state.disabled,
    )
    st.session_state[FEATURE_INDEX] = ChatGPTFeature.index(feature)
    feature = ChatGPTFeature.value_of(feature)
    return feature


def app():
    image = Image.open("images/zunda-icon.png")
    st.set_page_config(page_title="michat - DEMO", page_icon=image)
    st.title("michat")

    session_init()

    with st.sidebar:
        view_mode = mode_options()
        speaker_id = voice_options()
        feature = feautre_option()

    if view_mode == "chat":
        chat_view()
    elif view_mode == "image":
        image_view()

    webrtc = WebRTCRecorder()
    logger.debug("session_state: {}".format(st.session_state))
    logger.debug("player state: {}".format(webrtc.webrtc_ctx.state))
    webrtc.listen()  # busy loop here
    generated, emotions = webrtc.generate(feature)
    logger.info("generated: {}".format(generated))
    logger.info("emotions: {}".format(emotions))

    generated_index = st.session_state[GENERATED_INDEX]
    read_index = st.session_state[READ_INDEX]
    logger.debug("main:read_index: {}".format(read_index))
    logger.debug("main:gen_index: {}".format(generated_index))

    # re-reder view
    # TODO: are there any other good way??
    if (
        generated_index is not None
        and read_index is not None
        and generated_index > read_index
        and not st.session_state[RERUNED]
    ):
        st.session_state[RERUNED] = True
        st.experimental_rerun()
        # not excecuted here
    else:
        st.session_state[RERUNED] = False

    if (
        generated_index is not None
        and read_index is not None
        and generated_index > read_index
    ):
        webrtc.audio_play(speaker_id)


if __name__ == "__main__":
    app()
