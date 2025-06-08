robot
تشغيل الاستماع
إيقاف مؤقت
Exception in thread Thread-10 (listen_loop):
Traceback (most recent call last):
  File "/usr/lib/python3.11/threading.py", line 1038, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.11/threading.py", line 975, in run
     self._target(*self._args, **self._kwargs)
  File "/home/admin/RoboNex/Robot.py", line 341, in listen_loop
    recognize_from_microphone(self.robot, stop_event)
  File "/home/admin/RoboNex/Robot.py", line 248, in recognize_from_microphone
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/speech.py", line 1115, in __init__
    _call_hr_fn(
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/interop.py", line 62, in _call_hr_fn
    _raise_if_failed(hr)
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/interop.py", line 55, in _raise_if_failed
    __try_get_error(_spx_handle(hr))
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/interop.py", line 50, in __try_get_error
    raise RuntimeError(message)
RuntimeError: Exception with error code: 
[CALL STACK BEGIN]

/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.extension.audio.sys.so(+0xf8cc) [0x7fa16df8cc]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xa6b14) [0x7fa2a76b14]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x18ae10) [0x7fa2b5ae10]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xe02cc) [0x7fa2ab02cc]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x18f134) [0x7fa2b5f134]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xa6b14) [0x7fa2a76b14]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x18ae10) [0x7fa2b5ae10]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xddf6c) [0x7fa2aadf6c]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xe1630) [0x7fa2ab1630]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x147240) [0x7fa2b17240]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x147240) [0x7fa2b17240]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x106f38) [0x7fa2ad6f38]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x139770) [0x7fa2b09770]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x98770) [0x7fa2a68770]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x13860c) [0x7fa2b0860c]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x90a84) [0x7fa2a60a84]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(recognizer_create_speech_recognizer_from_config+0x110) [0x7fa2ba26c4]
[CALL STACK END]

Exception with an error code: 0xe (SPXERR_MIC_NOT_AVAILABLE)
2
nameneutral1
تشغيل الاستماع
إيقاف مؤقت
Exception in thread Thread-11 (listen_loop):
Traceback (most recent call last):
  File "/usr/lib/python3.11/threading.py", line 1038, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.11/threading.py", line 975, in run
     self._target(*self._args, **self._kwargs)
  File "/home/admin/RoboNex/Robot.py", line 341, in listen_loop
    recognize_from_microphone(self.robot, stop_event)
  File "/home/admin/RoboNex/Robot.py", line 248, in recognize_from_microphone
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/speech.py", line 1115, in __init__
    _call_hr_fn(
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/interop.py", line 62, in _call_hr_fn
    _raise_if_failed(hr)
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/interop.py", line 55, in _raise_if_failed
    __try_get_error(_spx_handle(hr))
  File "/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/interop.py", line 50, in __try_get_error
    raise RuntimeError(message)
RuntimeError: Exception with error code: 
[CALL STACK BEGIN]

/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.extension.audio.sys.so(+0xf8cc) [0x7fa16df8cc]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xa6b14) [0x7fa2a76b14]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x18ae10) [0x7fa2b5ae10]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xe02cc) [0x7fa2ab02cc]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x18f134) [0x7fa2b5f134]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xa6b14) [0x7fa2a76b14]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x18ae10) [0x7fa2b5ae10]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xddf6c) [0x7fa2aadf6c]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0xe1630) [0x7fa2ab1630]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x147240) [0x7fa2b17240]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x147240) [0x7fa2b17240]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x106f38) [0x7fa2ad6f38]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x139770) [0x7fa2b09770]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x98770) [0x7fa2a68770]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x13860c) [0x7fa2b0860c]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(+0x90a84) [0x7fa2a60a84]
/home/admin/RoboNex/venv/lib/python3.11/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.so(recognizer_create_speech_recognizer_from_config+0x110) [0x7fa2ba26c4]
[CALL STACK END]

Exception with an error code: 0xe (SPXERR_MIC_NOT_AVAILABLE)
/home/admin/RoboNex/test.py:146: RuntimeWarning: No channels have been set up yet - nothing to clean up!  Try cleaning up at the end of your program instead!
  GPIO.cleanup()  # Clean up GPIO resources\
