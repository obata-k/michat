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

    def listen(self):
        status_box = st.empty()
        ts = AudioTranscriber()
        chat = ChatGPT(140)
        speaker = Audio(3)

        while True:
            if self.webrtc_ctx.audio_receiver:
                try:
                    audio_frames = self.webrtc_ctx.audio_receiver.get_frames(
                        timeout=0.5
                    )
                except queue.Empty:
                    status_box.warning("No frame arrived.")
                    continue

                status_box.info("何か聞いてね！")

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

        audio_buffer = st.session_state[AUDIO_BUFFER]
        audio_placeholder = st.empty()

        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            status_box.success("ばいばい！")
            try:
                wav_bytes = io.BytesIO()
                audio_buffer.export(wav_bytes, format="wav")
                for t in ts.listen(wav_bytes):
                    message(t, is_user=True)
                    with open(SYSTEM, "r") as sf:
                        system_text = sf.read()
                    generated = chat.generate(system_text, t)
                    speaker.transform(generated)
                    speaker.save_wav(OUTPUT)
                    with open(OUTPUT, "rb") as ow:
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
                    message(generated)
            except Exception as e:
                st.error(f"Error while transcripting: {e}")

            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()


def app():
    st.title("michat")
    st.write("ミクとお話しよ！")

    st_webrtc_logger = logging.getLogger("streamlit_webrtc")
    st_webrtc_logger.setLevel(logging.INFO)

    webrtc = WebRTCRecorder()
    webrtc.listen()


if __name__ == "__main__":
    app()
