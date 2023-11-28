import tkinter as tk
import threading
import pyaudio
import wave
import os
import time
import sv_ttk
import subprocess
import sys

from src.video_generation import avatar_api
from src.doctor_notes import note_generator
from src.speech_recognition import speech_to_text
from src.text_correction import text_correction

class GPConversationCaptureApp:
    def __init__(self, root):
        self.root = root
        sv_ttk.set_theme("dark")
        self.root.geometry("400x200")
        self.root.title("GP Conversation Capture")

        # Initialize button states
        self.script_button_state = "black"
        self.video_button_state = "black"
        self.notes_button_state = "black"
        self.all_button_state = "black"

        # Add title
        title_label = tk.Label(self.root, text="General Practitioner Conversation Capture", font=("Arial", 16))
        title_label.pack()

        self.record_button = tk.Button(root, text="Record", command=self.start_recording, fg="black")
        self.record_button.pack(pady = 50)

        self.is_recording = False
        self.frames = []

         # Timer and light setup
        self.timer_light_frame = tk.Frame(root)
        self.light_label = tk.Label(self.timer_light_frame, text="●", fg="black")
        self.light_label.pack(side=tk.LEFT)
        self.timer_label = tk.Label(self.timer_light_frame, text="00:00")
        self.timer_label.pack(side=tk.LEFT)
        # self.timer_light_frame.pack()

    def start_recording(self):
        self.is_recording = True
        self.record_thread = threading.Thread(target=self.record_audio)
        self.record_thread.start()
        self.record_button.config(text="Stop", command=self.stop_recording, fg="black")

        self.timer_light_frame.pack(pady = 15)  # Show the frame with the timer and light
        self.update_timer(0)
        self.start_flashing()


    def stop_recording(self):
        self.is_recording = False
        self.record_thread.join()
        self.record_button.pack_forget()
        self.timer_light_frame.pack_forget()

        # # Start the process_audio method in a new thread
        # processing_thread = threading.Thread(target=self.process_audio)
        # processing_thread.start()

        self.create_file_buttons()

    # def process_audio(self):
    #     script, sp0, sp1 = speech_to_text.getRawScript()
    #     self.script = script
    #     self.sp0 = sp0
    #     self.sp1 = sp1

    #     # Call method to update UI or trigger next actions in the main thread
    #     self.root.after(0, self.post_process_audio)

    def record_audio(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
        self.frames = []

        while self.is_recording:
            data = self.stream.read(1024)
            self.frames.append(data)

        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

        self.save_recording()

    def save_recording(self):
        output_file_path = os.path.join('outputs', "recording.wav")
        wave_file = wave.open(output_file_path, 'wb')
        wave_file.setnchannels(1)
        wave_file.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wave_file.setframerate(44100)
        wave_file.writeframes(b''.join(self.frames))
        wave_file.close()

    def create_file_buttons(self):
         # Hide the file generation and show files button
        for widget in self.root.winfo_children():
            widget.pack_forget()
        
        # Add title
        tk.Label(self.root, text="General Practitioner Conversation Capture", font=("Arial", 16)).pack()
        tk.Label(self.root, text="Click to Generate:", font=("Arial", 12)).pack()

        self.script_button = tk.Button(self.root, text="Conversation Script", command=self.generate_conversation_script, fg=self.script_button_state)
        self.script_button.pack()

        self.video_button = tk.Button(self.root, text="Animated Video", command=self.generate_animated_video, fg=self.video_button_state)
        self.video_button.pack()

        self.notes_button = tk.Button(self.root, text="Doctor Notes", command=self.generate_doctor_notes, fg=self.notes_button_state)
        self.notes_button.pack()
        
        self.all_button = tk.Button(self.root, text="All", command=self.generate_all, fg=self.all_button_state)
        self.all_button.pack()

        tk.Button(self.root, text="Show Files", command=self.display_output_files, fg="black").pack(pady = 7)

    def display_output_files(self):
        # Hide the file generation and show files button
        for widget in self.root.winfo_children():
            widget.pack_forget()

        # Add title
        tk.Label(self.root, text="General Practitioner Conversation Capture", font=("Arial", 16)).pack()
        tk.Label(self.root, text="Files Avaliable:", font=("Arial", 12)).pack()

       # Check if output folder exists
        if os.path.exists('outputs'):
            # List all files in the output folder
            output_files = os.listdir('outputs')

        for file in output_files:
            file_path = os.path.join('outputs', file)
            btn = tk.Button(self.root, text=file, command=lambda f=file_path: self.open_file(f), fg="black")
            btn.pack()
        
        self.back_button = tk.Button(self.root, text="Back", command=self.create_file_buttons, fg="black")
        self.back_button.pack(pady = 6)

    def open_file(self, file_path):
        # Open file with default application
        subprocess.call(('open', file_path)) if sys.platform == "darwin" else subprocess.call(('xdg-open', file_path))

    def generate_conversation_script(self):
        # Placeholder for generating conversation script
        if(self.script_button_state != 'green'):
            avatar_thread = threading.Thread(target=self.generate_script, args=(self.script, self.sp0, self.sp1))
            avatar_thread.start()
            print("Generating Conversation Script")
            self.script_button_state = "green"
            self.script_button.config(fg=self.script_button_state)
            self.check_and_update_all_button()
    
    def generate_script(self, full_dialogue, sp0, sp1):
        print("Generating Animated Video")
        script, docGender, patGender = text_correction.correctText(full_dialogue, sp0, sp1)
        self.script = script
        self.docGender = docGender
        self.patGender = patGender

    def generate_animated_video(self):
        # Placeholder for generating animated video
        if(self.video_button_state != 'green'):
            self.generate_conversation_script()
            avatar_thread = threading.Thread(target=self.generate_avatar, args=(self.script, self.docGender, self.patGender))
            avatar_thread.start()
            self.video_button_state = 'green'
            self.video_button.configure(fg=self.video_button_state)  # Change button color to green after action
            self.check_and_update_all_button()

    def generate_avatar(self, full_dialogue, docGender, patGender):
        print("Generating Animated Video")
        avatar_api.createVideo(full_dialogue, docGender, patGender)

    def generate_doctor_notes(self):
        # Placeholder for generating doctor notes
        if(self.notes_button_state != 'green'):
            avatar_thread = threading.Thread(target=self.generate_notes, args=(self.script))
            avatar_thread.start()
            print("Generating Doctor Notes")
            self.notes_button_state = 'green'
            self.notes_button.configure(fg=self.notes_button_state)  # Change button color to green after action
            self.check_and_update_all_button()

    def generate_avatar(self, full_dialogue):
        print("Generating Animated Video")
        note_generator.generateNotes(full_dialogue)

    def generate_all(self):
        self.generate_conversation_script()
        self.generate_animated_video()
        self.generate_doctor_notes()
        self.check_and_update_all_button()

    
    def check_and_update_all_button(self):
        if (self.script_button_state == "green" and
            self.video_button_state == "green" and
            self.notes_button_state == "green"):
            self.all_button_state = "green"
        else:
            self.all_button_state = "black"
        self.all_button.config(fg=self.all_button_state)

    def update_timer(self, elapsed_time):
        if self.is_recording:
            formatted_time = time.strftime('%M:%S', time.gmtime(elapsed_time))
            self.timer_label.config(text=formatted_time)
            self.root.after(1000, self.update_timer, elapsed_time + 1)

    def start_flashing(self):
        if self.is_recording:
            current_color = self.light_label.cget("fg")
            new_color = "red" if current_color == "black" else "black"
            self.light_label.config(fg=new_color)
            self.root.after(500, self.start_flashing)

if __name__ == "__main__":
    root = tk.Tk()
    app = GPConversationCaptureApp(root)
    root.mainloop()
