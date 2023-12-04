import webvtt
import rich
import time
import re
import torch
import rich
from importlib.metadata import version
from rich.progress import TaskProgressColumn
from pyannote.audio import Pipeline
import subprocess
from pyannote.audio.pipelines.utils.hook import ProgressHook
from pydub import AudioSegment
from datetime import timedelta
from transformers import pipeline
from pydub import AudioSegment

from transformers import logging
logging.set_verbosity_warning()

def getRawScript():

    #############################################
    # Constants
    #############################################
    FILE_NAME = "outputs/recording.wav"
    HF_API_KEY = ""

    #############################################
    # Step 1: Transcribe file
    #############################################
    start_time = time.perf_counter()
    rich.print(f"[bold gold1]Transcribing {FILE_NAME}...")
    subprocess.run(["whisperx", "--language", "en", "--output_format", "vtt", "--compute_type", "int8", FILE_NAME])
    rich.print(f"[bold chartreuse1]Transcribed {FILE_NAME}. ")

    #############################################
    # Step 2: Get captions into Python objects
    #############################################
    def millisec(timeStr):
        spl = timeStr.split(":")
        s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000)
        return s

    captions = [[(int)(millisec(caption.start)), (int)(millisec(caption.end)),  caption.text] for caption in webvtt.read('recording.vtt')]
    print(*captions[:8], sep='\n')

    #############################################
    # Step 3: Diarization (prepend with silent audio segment)
    #############################################
    audio = AudioSegment.from_wav(FILE_NAME)
    spacermilli = 2000
    spacer = AudioSegment.silent(duration=spacermilli)
    audio = spacer.append(audio, crossfade=0)

    audio.export('audio.wav', format='wav')

    #############################################
    # Step 4: Diarization
    #############################################

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.0",
        use_auth_token=HF_API_KEY
    )

    start_time = time.process_time()

    with ProgressHook() as hook:
        diarization = pipeline("audio.wav", hook = hook, num_speakers=2)

    with open("diarization.txt", "w") as text_file:
        text_file.write(str(diarization))

    print(f"Diarization complete! (took: {time.process_time() - start_time:.2f}s)")

    #############################################
    # Step 5
    #############################################
    dz = open('diarization.txt').read().splitlines()
    dzList = []
    for l in dz:
        start, end =  tuple(re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=l))
        start = millisec(start) - spacermilli
        end = millisec(end)  - spacermilli
        doctor = not re.findall('SPEAKER_01', string=l)
        dzList.append([start, end, doctor])

    def remove_overlaps(segments: list[int | bool]) -> list[int | bool]:
        """
        Removes overlaps in the diarization output.
        """
        last_timestamp = segments[-1][1]
        res = []
        current_speaker = None
        for i in range(last_timestamp):
            found_segments = []
            for segment in segments:
                if segment[0] > i:
                    break
                if i in range(segment[0], segment[1]):
                    found_segments.append(segment)
            if not found_segments:
                continue
            found_segments.sort(key = lambda x: x[1] - x[0])
            speaker = found_segments[0]
            if current_speaker is None or current_speaker[2] != speaker[2]:
              if current_speaker is not None:
                    current_speaker[1] = i
                    res.append(current_speaker)
            current_speaker = [i, None, speaker[2]]
        return res

    dzList = remove_overlaps(dzList)

    #############################################
    # Step 6
    #############################################
    def get_dz(start: int, stop: int) -> list[int | bool]:
        global dzList
        x = range(start, stop)
        overlaps = []
        for dz in dzList:
            if dz[0] > stop:
               break
            if dz[1] < start:
                continue
            if dz[0] < start and dz[1] > end:
                return dz
            y = range(dz[0], dz[1])
            overlap = range(max(x[0], y[0]), min(x[-1], y[-1])+1)
            overlaps.append((len(overlap), dz))
        return max(overlaps, key = lambda x: x[0])[1] if overlaps else []

    script = ""
    for caption in captions:
        start = caption[0]
        start = start / 1000.0
        startStr = '{0:02d}:{1:02d}:{2:02.2f}'.format((int)(start // 3600),
                                                (int)(start % 3600 // 60),
                                                start % 60)

        dz = get_dz(caption[0], caption[1])
        if not dz:
            break

        name_tag = "[SPEAKER_00]" if dz[2] else "[SPEAKER_01]"
        saying = caption[2]
        script += f"{startStr} {name_tag} {saying}\n"

    print(script)

    #############################################
    # Step 7: Gender classification
    #############################################
    def classify(path) -> bool:
        """
        Outputs whether the person is female.
        """
        classifier = pipeline(task="audio-classification", model="alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech")
        preds = classifier(path)
        preds = [{"score": round(pred["score"], 4), "label": pred["label"]} for pred in preds]
        male = [p for p in preds if p['label'] == 'male'][0]['score']
        female = [p for p in preds if p['label'] == 'female'][0]['score']
        return female > male

    def split_segment(path: str, output_path: str, start_ms: int, end_ms: int):
        """
        Splits an audio segment into a start and end millisecond period.
        """
        sound = AudioSegment.from_file(path)
        new_sound = sound[start_ms:end_ms]
        new_sound.export(output_path, format = "wav")

    def genders(path) -> tuple[bool, bool]:
        """
        Returns whether speaker 0 and speaker 1 are female as two bools.
        True = female.
        """
        # Get diarization time periods for each speaker
        speaker0 = [s for s in dzList if s[2] == True][:3]
        speaker1 = [s for s in dzList if s[2] == False][:3]

        if not speaker0 or not speaker1:
            raise RuntimeError("missing speaking segments")

        # Detecting if speaker 0 is female
        sp0_results = []
        for seg in speaker0:
            split_segment(path, "segment.wav", seg[0], seg[1])
            sp0_results.append(classify("segment.wav"))
        sp0_female = sum(sp0_results) >= 2

        # Detecting if speaker 1 is female
        sp1_results = []
        for seg in speaker1:
            split_segment(path, "segment.wav", seg[0], seg[1])
            sp1_results.append(classify("segment.wav"))
        sp1_female = sum(sp1_results) >= 2

        return sp0_female, sp1_female


    sp0, sp1 = genders(FILE_NAME)
    print(f"[SPEAKER_00]: {'female' if sp0 else 'male'}")
    print(f"[SPEAKER_01]: {'female' if sp1 else 'male'}")

    return script, sp0, sp1
