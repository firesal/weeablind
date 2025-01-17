# This file contains all functions related to diarizing a video including optimization and processing a speech diary (rttm file)
# These functions use a functional approach as I didn't wanted to group them and not bloat the video class with such specific functions
# Perhaps going forward I should abstract diary entries as their own objects similar to dub_line, but I haven't decidded yet as diaries might be useful for voice cloning as well

import app_state
import utils
from Voice import Voice
from pyannote.audio import Pipeline
import torchaudio.transforms as T
import torchaudio
import random

pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization@2.1", use_auth_token="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")

# Read RTTM files generated by Pyannote into an array containing the speaker, start, and end of their speech in the audio
def load_diary(file):
	diary = []
	with open(file, 'r', encoding='utf-8') as diary_file:
		for line in diary_file.read().strip().split('\n'):
			line_values = line.split(' ')
			diary.append([line_values[7], float(line_values[3]), float(line_values[4])])
	total_speakers = len(set(line[0] for line in diary))
	app_state.speakers = initialize_speakers(total_speakers)
	return diary

# Time Shift the speech diary to be in line with the start time
def update_diary_timing(diary, start_time):
	return [[int(line[0].split('_')[1]), line[1] + start_time, line[2]] for line in diary]

def initialize_speakers(speaker_count):
	speakers = []
	speaker_options = app_state.sample_speaker.list_speakers()
	for i in range(speaker_count):
		speakers.append(Voice(Voice.VoiceType.COQUI, f"Voice {i}"))
		speakers[i].set_voice_params('tts_models/en/vctk/vits', random.choice(speaker_options))
	return speakers

def find_nearest_speaker(diary, sub):
	return diary[
		utils.find_nearest(
			[diary_entry[1] for diary_entry in diary],
			sub.start
		)
	][0]



def optimize_audio_diarization(video):
	crop = video.crop_audio()
	waveform, sample_rate = torchaudio.load(crop)
	# Apply noise reduction
	noise_reduce = T.Vad(sample_rate=sample_rate)
	clean_waveform = noise_reduce(waveform)
	
	# Normalize audio
	normalize = T.Resample(orig_freq=sample_rate, new_freq=sample_rate)
	normalized_waveform = normalize(clean_waveform)

	return normalized_waveform, sample_rate

def run_diarization(video):
	output = utils.get_output_path(video.file, ".rttm")
	optimized, sample_rate = optimize_audio_diarization(video)
	diarization = pipeline({"waveform": optimized, "sample_rate": sample_rate})
	with open(output, "w") as rttm:
		diarization.write_rttm(rttm)
	diary = load_diary(output)
	diary = update_diary_timing(diary, video.start_time)
	for sub in video.subs_adjusted:
		sub.voice = find_nearest_speaker(diary, sub)
