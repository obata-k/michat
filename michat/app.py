import io
import logging
import base64
import time
import numpy as np
import queue
from pathlib import Path
from streamlit_chat import message

import pydub
import streamlit as st
from lib.speak import ChatGPT, Audio
from lib.transcript import AudioTranscriber
from streamlit_webrtc import WebRtcMode, webrtc_streamer


# stremlit status
AUDIO_BUFFER = "audio_buffer"
BOT_MESSAGES = "bot_messages"
USR_MESSAGES = "usr_messages"

# chatgpt
SYSTEM = Path("system.txt")
OUTPUT = Path("output.wav")


class WebRTCRecorder:
    def __init__(self):
        self.webrtc_ctx = webrtc_streamer(
            key="michat",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            },
            media_stream_constraints={"video": False, "audio": True},
            audio_receiver_size=1024,
        )

        if AUDIO_BUFFER not in st.session_state:
            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()
        if BOT_MESSAGES not in st.session_state:
            st.session_state[BOT_MESSAGES] = []
        if USR_MESSAGES not in st.session_state:
            st.session_state[USR_MESSAGES] = []

    def listen(self):
        self.status_box = st.empty()

        if not self.webrtc_ctx.state.playing:
            return

        while True:
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

    def request(self):
        audio_buffer = st.session_state[AUDIO_BUFFER]
        ts = AudioTranscriber()
        chat = ChatGPT(140)
        speaker = Audio(3)

        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            try:
                wav_bytes = io.BytesIO()
                audio_buffer.export(wav_bytes, format="wav")
                t = ts.listen(wav_bytes)
                st.session_state[USR_MESSAGES].append(t)
                with open(SYSTEM, "r") as sf:
                    system_text = sf.read()
                generated = chat.generate(system_text, t)
                speaker.transform(generated)
                speaker.save_wav(OUTPUT)
                self.__background_play(OUTPUT)
                st.session_state[BOT_MESSAGES].append(generated)
            except Exception as e:
                st.error(f"Error while transcripting: {e}")

            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()

    def view(self):
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


def app():
    st.title("michat")
    st.subheader("美少女アシスタント - micha")

    st_webrtc_logger = logging.getLogger("streamlit_webrtc")
    st_webrtc_logger.setLevel(logging.INFO)

    webrtc = WebRTCRecorder()
    webrtc.listen()
    webrtc.request()
    webrtc.view()


if __name__ == "__main__":
    app()