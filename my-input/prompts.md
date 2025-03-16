# First prompt
I want to create a POC of voice assistant with function calling.
The first implementation should be simple and straight forward.
It should be fully working. One function call and full converstaion mode in real time.

Inormation about my idea is in @input.md 
Fragments of documentation are in @openAI-sdk 

First try was a fail @test1.py. First think by analyzing available docs. Look online @web if you need to. Then analyze my fail and create your solution!

## Problems
(venv) tako@BookMacAir VoiceAssistant % python3 voice_assistant.py
2025-03-15 20:09:35,443 [INFO] Creating session...
2025-03-15 20:09:36,229 [INFO] Session created successfully with ID: sess_BBRB2QyfFIlRnelTKfvLn
Select input mode (1 for audio, 2 for text): 1
Press Enter to commit audio...
2025-03-15 20:09:40,973 [ERROR] Unexpected error: BaseEventLoop.create_connection() got an unexpected keyword argument 'extra_headers'
(venv) tako@BookMacAir VoiceAssistant % python3 voice_assistant.py
2025-03-15 20:10:57,333 [INFO] Creating session...
2025-03-15 20:10:58,096 [INFO] Session created successfully with ID: sess_BBRCMrkmDgNxArXfR6yxy
Select input mode (1 for audio, 2 for text): 1
Press Enter to commit audio...
2025-03-15 20:11:00,040 [INFO] Audio capture started. Speak continuously; press Enter to commit the current buffer.
2025-03-15 20:11:00,550 [ERROR] Unexpected error: server rejected WebSocket connection: HTTP 403
(venv) tako@BookMacAir VoiceAssistant % python3 voice_assistant.py
2025-03-15 20:15:14,596 [INFO] Creating session...
2025-03-15 20:15:15,271 [INFO] Session created successfully with ID: sess_BBRGVNWRbcP1AolBzsMXw
Select input mode (1 for audio, 2 for text): 1
Press Enter to commit audio...
2025-03-15 20:15:17,958 [INFO] Audio capture started. Speak continuously; press Enter to commit the current buffer.
2025-03-15 20:15:18,454 [ERROR] Unexpected error: server rejected WebSocket connection: HTTP 403
(venv) tako@BookMacAir VoiceAssistant % python3 voice_assistant.py
2025-03-15 20:16:20,060 [INFO] Creating session...
2025-03-15 20:16:20,687 [INFO] Session created successfully with ID: sess_BBRHYzsUuahxnoLj4YPyj
Select input mode (1 for audio, 2 for text): 1
Press Enter to commit audio...
2025-03-15 20:16:22,762 [INFO] Audio capture started. Speak continuously; press Enter to commit the current buffer.
2025-03-15 20:16:23,272 [ERROR] Unexpected error: server rejected WebSocket connection: HTTP 403

# No real time just audio
Let's change approach. We have a little promblem with realtime. Create solution to normal audio.

I have moved realtime docs to @openAI-sdk/realtime 
i have renamed file to @fail-voice_assistant-realtime.py - history - do not modify it, create new file

docs about using audio is here @audio.md and model is here @gpt-4o.md 

input is the same @input.md

## Went well but there are some trobules with audio recording - im on the highway at the moment...
info: im connected to mac via airpods, further testing.
prompt
create an recording module

it should have extensive needed configuration

for i want to have if name == main for testing purposes