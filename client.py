import socket
import json
import speech_recognition as sr
import spacy
import cv2
import pygame
import time
import tempfile
from gtts import gTTS
from io import BytesIO

tcp_port = 1672
tcp_ip = '127.0.0.1'
buf_size = 1024
# '''
nlp = spacy.load("en_core_web_sm")

def speech_to_text():
    # Create a speech recognition object
    recognizer = sr.Recognizer()
    try:
        # Capture audio from the microphone
        with sr.Microphone() as source:
            print("\n\nSay something:")
            audio = recognizer.listen(source, timeout=3)  # Adjust the timeout as needed
    except:
        print("Ouch! Timed out....")
        return

    try:
        # Use Google Web Speech API to recognize the audio
        text = recognizer.recognize_google(audio)
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Error with the speech recognition service; {e}")
        return None
    
def extract_nouns_and_objects_spacy(text):
    # Process the text using spaCy
    doc = nlp(text)

    # Extract nouns and objects
    nouns = [token.text for token in doc if token.pos_ == 'NOUN']
    objects = [token.text.lower() for token in doc if token.pos_ in ('NOUN', 'VERB')]  # Nouns and verbs

    return nouns, objects

#text to speech            
def speak(text, language='en'):
    mp3_fp = tempfile.NamedTemporaryFile(delete=False)
    tts = gTTS(text, lang=language)
    tts.write_to_fp(mp3_fp)
    mp3_fp.close()  # Close the file before passing it to pygame
    return mp3_fp.name  # Return the file path

# '''
print("[INFO] Creating Socket...")
s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
print("[INFO] Socket successfully created")

print("[INFO] Connecting Socket to port",tcp_port)
s.connect((tcp_ip,tcp_port))
print("[INFO] Socket connected successfully to port",tcp_port)

# =========================================================
n=1
#--- speech
pygame.init()
pygame.mixer.init()

while True:
    # Convert speech to text
    start = int(input("\nTo ask something, press 1. To close program, press 0 >> "))

    if(start==0):
        msg = json.dumps({0:"quit"})
        msgpckt = msg.encode()
        s.send(msgpckt)
        break

    recognized_text = speech_to_text()

    # Extract nouns and objects using spaCy
    if recognized_text:
        nouns_spacy, objects_spacy = extract_nouns_and_objects_spacy(recognized_text)
        # print("Nouns (spaCy):", nouns_spacy)
        print("Objects (spaCy):", objects_spacy)

        msg = json.dumps({0:objects_spacy})
        msgpckt = msg.encode()

        s.send(msgpckt)
    else:
        continue
    
    data = s.recv(buf_size)
    msg = json.loads(data.decode())

    if(msg.get('0')=="1"):
        display_file = "output.jpg"
        display_msg = "Found IT!"
        closest = msg.get('1')
        print(closest)
        print(type(closest))
        # print(type(closest[0]))
        # print(type(closest))
        for i in closest:
            speechstring = i+" is near "+closest[i]
            sound_file_path = speak(speechstring)
            pygame.mixer.music.load(sound_file_path)
            pygame.mixer.music.play()
            time.sleep(2)
    else:
        display_file = "not_found.png"
        display_msg = "Oops!"

        speechstring = msg.get('1')
        sound_file_path = speak(speechstring)
        pygame.mixer.music.load(sound_file_path)
        pygame.mixer.music.play()
        time.sleep(2)

    while True:
        display_frame = cv2.imread(display_file)
        cv2.imshow(display_msg, display_frame)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyWindow(display_msg)
            break

s.close()
print("\n[INFO] Socket disconnected successfully")