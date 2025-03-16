Audio
Learn how to turn audio into text or text into audio.

Related guide: Speech to text
Create speech
POST
 
https://api.openai.com/v1/audio/speech
Generates audio from the input text.

Request body

input
string
Required
The text to generate audio for. The maximum length is 4096 characters.
model
string
Required
One of the available TTS models: tts-1 or tts-1-hd
voice
string
Required
The voice to use when generating the audio. Supported voices are alloy, ash, coral, echo, fable, onyx, nova, sage and shimmer. Previews of the voices are available in the Text to speech guide.
response_format
string
Optional
Defaults to mp3
The format to audio in. Supported formats are mp3, opus, aac, flac, wav, and pcm.
speed
number
Optional
Defaults to 1
The speed of the generated audio. Select a value from 0.25 to 4.0. 1.0 is the default.
Returns

The audio file content.

Example request
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "The quick brown fox jumped over the lazy dog.",
    "voice": "alloy"
  }' \
  --output speech.mp3
Create transcription
POST
 
https://api.openai.com/v1/audio/transcriptions
Transcribes audio into the input language.

Request body

file
file
Required
The audio file object (not file name) to transcribe, in one of these formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
model
string or "whisper-1"
Required
ID of the model to use. Only whisper-1 (which is powered by our open source Whisper V2 model) is currently available.
language
string
Optional
The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency.
prompt
string
Optional
An optional text to guide the model's style or continue a previous audio segment. The prompt should match the audio language.
response_format
string
Optional
Defaults to json
The format of the output, in one of these options: json, text, srt, verbose_json, or vtt.
temperature
number
Optional
Defaults to 0
The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.
timestamp_granularities[]
array
Optional
Defaults to segment
The timestamp granularities to populate for this transcription. response_format must be set verbose_json to use timestamp granularities. Either or both of these options are supported: word, or segment. Note: There is no additional latency for segment timestamps, but generating word timestamps incurs additional latency.
Returns

The transcription object or a verbose transcription object.


Default

Word timestamps

Segment timestamps
Example request
curl https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@/path/to/file/audio.mp3" \
  -F model="whisper-1"
Response
{
  "text": "Imagine the wildest idea that you've ever had, and you're curious about how it might scale to something that's a 100, a 1,000 times bigger. This is a place where you can get to do that."
}
Create translation
POST
 
https://api.openai.com/v1/audio/translations
Translates audio into English.

Request body

file
file
Required
The audio file object (not file name) translate, in one of these formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
model
string or "whisper-1"
Required
ID of the model to use. Only whisper-1 (which is powered by our open source Whisper V2 model) is currently available.
prompt
string
Optional
An optional text to guide the model's style or continue a previous audio segment. The prompt should be in English.
response_format
string
Optional
Defaults to json
The format of the output, in one of these options: json, text, srt, verbose_json, or vtt.
temperature
number
Optional
Defaults to 0
The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.
Returns

The translated text.

Example request
curl https://api.openai.com/v1/audio/translations \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@/path/to/file/german.m4a" \
  -F model="whisper-1"
Response
{
  "text": "Hello, my name is Wolfgang and I come from Germany. Where are you heading today?"
}
The transcription object (JSON)
Represents a transcription response returned by model, based on the provided input.

text
string
The transcribed text.
OBJECT The transcription object (JSON)
{
  "text": "Imagine the wildest idea that you've ever had, and you're curious about how it might scale to something that's a 100, a 1,000 times bigger. This is a place where you can get to do that."
}
The transcription object (Verbose JSON)
Represents a verbose json transcription response returned by model, based on the provided input.

duration
number
The duration of the input audio.
language
string
The language of the input audio.
segments
array
Segments of the transcribed text and their corresponding details.

Show properties
text
string
The transcribed text.
words
array
Extracted words and their corresponding timestamps.

Show properties
OBJECT The transcription object (Verbose JSON)
{
  "task": "transcribe",
  "language": "english",
  "duration": 8.470000267028809,
  "text": "The beach was a popular spot on a hot summer day. People were swimming in the ocean, building sandcastles, and playing beach volleyball.",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 3.319999933242798,
      "text": " The beach was a popular spot on a hot summer day.",
      "tokens": [
        50364, 440, 7534, 390, 257, 3743, 4008, 322, 257, 2368, 4266, 786, 13, 50530
      ],
      "temperature": 0.0,
      "avg_logprob": -0.2860786020755768,
      "compression_ratio": 1.2363636493682861,
      "no_speech_prob": 0.00985979475080967
    },
    ...
  ]
