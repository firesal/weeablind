# This file just has an MVP function, a whole bunch of functions and testing things that'll be refactored.

import pyttsx3
import ffmpeg
import srt
from TTS.api import TTS
import numpy as np
import re
import Voice
from pydub.playback import play
from pydub import AudioSegment
from pydub.effects import speedup
from audiotsm import phasevocoder, wsola
from audiotsm.io.wav import WavReader, WavWriter
from yt_dlp import YoutubeDL

test_video_name = "saiki.mkv"

# READ SUBS
def get_subs(file):
	output = f"output/{file.split('.')[0]}.srt"
	# (
	# 	ffmpeg
	# 	.input(file)
	# 	.output(output)
	# 	.run()
	# )
	with open(output, "r") as f:
		return list(srt.parse(f.read()))

# Read RTTM files generated by Pyannote into an array containing the speaker, start, and end of their speech in the audio
def read_diary(file):
	speech_diary = []
	with open(file, 'r') as diary_file:
		for line in diary_file.read().strip().split('\n'):
			line_values = line.split(' ')
			speech_diary.append([line_values[7], float(line_values[3]), float(line_values[4])])
	return speech_diary

# This function finds the closest index for the given value
def find_nearest(array, value):
	return (np.abs(np.asarray(array) - value)).argmin()

subs = get_subs(test_video_name)
speech_diary = read_diary("audio.rttm")

start_time = 94
end_time =  124 #1324
remove_xml = re.compile('<.*?>')

start_line = find_nearest([sub.start.total_seconds() for sub in subs], start_time)
end_line = find_nearest([sub.start.total_seconds() for sub in subs], end_time)
# Time Shift the speech diary to be in line with the start time
speech_diary_adjusted = [[line[0], line[1] + start_time, line[2]] for line in speech_diary]
speech_diary_adjusted = speech_diary_adjusted[find_nearest([line[1] for line in speech_diary_adjusted], start_time):find_nearest([line[1] for line in speech_diary_adjusted], end_line)]

# # Create unique speakers
total_speakers = len(set(line[0] for line in speech_diary)) # determine the total number of speakers in the diary
def initialize_speakers(speaker_count):
	speakers = []
	for i in range(total_speakers):
		speakers.append(Voice.SAPI5Voice([], f"Voice {i}"))
	return speakers
speakers = initialize_speakers(total_speakers)
# speakers[0] = Voice.Voice(Voice.Voice.VoiceType.COQUI)
# speakers[0].set_voice_params('tts_models/en/vctk/vits', 'p326')
# speakers[1] = Voice.CoquiVoice(Voice.Voice.VoiceType.COQUI)
# speakers[1].set_voice_params('tts_models/en/vctk/vits', 'p340')


total_duration = (end_time - start_time)*1000
# # empty_audio = AudioSegment.silent(duration=total_duration)
current_audio = AudioSegment.from_file(test_video_name)

subs_adjusted = subs[start_line:end_line]
for sub in subs_adjusted:
	sub.content = re.sub(remove_xml, '', sub.content)

# # Synth
def synth():
	for sub in subs_adjusted:
		text = re.sub(remove_xml, '', sub.content)
		# 🤔 How the FRICK does this line work? 🤔
		current_speaker = int(speech_diary_adjusted[find_nearest([line[1] for line in speech_diary_adjusted], sub.start.total_seconds())][0].split('_')[1])
		current_speaker.set_speed(60*int((len(text.split(' ')) / (sub.end.total_seconds() - sub.start.total_seconds()))))
		file_name = f"files/{sub.index}.wav"
		current_speaker.speak(text, file_name)
		print(text)
		empty_audio = empty_audio.overlay(AudioSegment.from_file(file_name), position=sub.start.total_seconds()*1000)
	empty_audio.export("new.wav")

currentSpeaker = speakers[0]
sampleSpeaker = currentSpeaker

default_sample_path = "./output/sample.wav"

def sampleVoice(text, output=default_sample_path):
	play(AudioSegment.from_file(sampleSpeaker.speak(text, output)))

def adjust_fit_rate(target_path, source_duration, destination_path=None):
	if destination_path == None:
		destination_path = target_path.split('.')[0] + '-timeshift.wav'
	duration = float(ffmpeg.probe(target_path)["format"]["duration"])
	sound = AudioSegment.from_wav(target_path)
	rate = duration*1/source_duration
	with WavReader(target_path) as reader:
		with WavWriter(destination_path, reader.channels, reader.samplerate) as writer:
			tsm = wsola(reader.channels, speed=rate)
			tsm.run(reader, writer)
	# speedup(sound, rate, 30, 50).export(destination_path, format="wav")
	# ffmpeg.input(target_path).filter('atempo', rate).output(destination_path).run(overwrite_output=True)
	return destination_path

def Download(link):
	YoutubeDL().download(link)

def get_snippet(start, end):
	return current_audio[start*1000:end*1000]

# Download("https://www.youtube.com/watch?v=VOjAlLoXOhQ")
