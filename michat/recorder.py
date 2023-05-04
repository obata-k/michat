import hashlib
import json
import queue
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pydub
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

# session_state parameters(keys)
AUDIO_BUFFER = "audio_buffer"
RECORDS = "records"
COUNTER = "counter"


class Counter:
    def __init__(self) -> None:
        self.index: int = 0
        self.total: Optional[int] = None

    def set_total(self, n):
        self.total = n

    def next(self):
        if self.total and self.index != self.total - 1:
            self.index += 1

    def previous(self):
        if self.index != 0:
            self.index -= 1

    @property
    def progress_percent(self) -> float:
        # include current item
        if self.total:
            return (self.index + 1) / self.total
        else:
            return 0.0


@dataclass
class Record:
    manuscript_index: int
    text: str
    wav_dir_path: Path

    @property
    def file_id(self):
        return hashlib.md5(
            (self.text + str(self.manuscript_index)).encode()
        ).hexdigest()

    @property
    def output_wav_name(self):
        return f"{self.file_id}.wav"

    @property
    def wav_file_path(self):
        return self.wav_dir_path / self.output_wav_name

    @property
    def record_info(self):
        return {"text": self.text, "file_name": self.output_wav_name}


@dataclass
class RecordStrage:
    all_manuscripts: List[str] = field(default_factory=list)
    id2record: Dict[int, Record] = field(default_factory=dict)

    @property
    def num_wav_files(self):
        return len(self.id2record)

    def export_record_info_as_json(self, record_info_path) -> None:
        with record_info_path.open("w") as f:
            json.dump(
                [record.record_info for _, record in self.id2record.items()],
                f,
                ensure_ascii=False,
                indent=4,
            )

    def export_unrecorded_texts_as_json(self, unrecorded_textx_path) -> None:
        if unrecorded_textx_path.exists():
            unrecorded_textx_path.unlink()

        recorded_indexes = set(
            [record.manuscript_index for _, record in self.id2record.items()]
        )
        results = []
        for i, text in enumerate(self.all_manuscripts):
            if i not in recorded_indexes:
                results.append(text)

        if results:
            with unrecorded_textx_path.open("w") as f:
                for text in results:
                    f.write(text + "\n")

    def compress_wav_files_into_zip(self, archive_filename, wav_dir_path):
        with zipfile.ZipFile(
            archive_filename, "w", zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for file_path in wav_dir_path.rglob("*"):
                archive.write(file_path, arcname=file_path.relative_to(wav_dir_path))


class WebRTCRecorder:
    def __init__(self, timeout=1):
        self.timeout = timeout
        self.webrtc_ctx = webrtc_streamer(
            key="sendonly-audio",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=256,
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            },
            media_stream_constraints={
                "audio": True,
            },
        )

        if AUDIO_BUFFER not in st.session_state:
            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()

    def listen(self, record):
        status_box = st.empty()

        while True:
            if self.webrtc_ctx.audio_receiver:
                try:
                    audio_frames = self.webrtc_ctx.audio_receiver.get_frames(
                        timeout=self.timeout
                    )
                except queue.Empty:
                    status_box.warning("No frame arrived.")
                    continue
                status_box.info("Now listening...")

                chunk = pydub.AudioSegment.empty()
                for audio_frame in audio_frames:
                    sound = pydub.AudioSegment(
                        data=audio_frame.to_ndarray().tobytes(),
                        sample_width=audio_frame.format.bytes,
                        frame_rate=audio_frame.sample_rate,
                        channels=len(audio_frame.layout.channels),
                    )
                    chunk += sound

                    if len(chunk) > 0:
                        st.session_state[AUDIO_BUFFER] += chunk
            else:
                break

        audio_buffer = st.session_state[AUDIO_BUFFER]
        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            status_box.success("Finish listening!")
            try:
                st.session_state[RECORDS].id2record[record.output_wav_name] = record
                audio_buffer.export(str(record.wav_file_path), format="wav")
            except BaseException:
                st.error("Error while writing wav to disk")

            st.session_state[AUDIO_BUFFER] = pydub.AudioSegment.empty()

