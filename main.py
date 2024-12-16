from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.list import OneLineListItem
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
import numpy as np
import sounddevice as sd
import soundfile as sf

# Parameters for FSK Modulation
fs = 44100  # Sampling frequency (44.1 kHz)
baud_rate = 300  # Baud rate (bits per second)
f1 = 1500  # Frequency for bit 0
f2 = 2500  # Frequency for bit 1
duration_per_bit = 1 / baud_rate  # Duration per bit in seconds

KV = """
MDBoxLayout:
    orientation: "vertical" 

    MDTopAppBar:
        title: "Text to List"
        left_action_items: [["comment"]]
        right_action_items: [["microphone", lambda x: app.on_microphone_button_pressed()], ["widgets"]]
        elevation: 2

    BoxLayout:
        orientation: "horizontal"  # Arrange widgets horizontally
        padding: [10, 60, 10, 10]  # Padding for inner widgets
        spacing: 10  # Space between widgets
        size_hint_y: None  # Don't let it stretch vertically
        height: "80dp"  # Fixed height for the BoxLayout
        pos_hint: {"top": 1}  # Position this layout at the top of the screen

        MDTextField:
            id: text_field
            hint_text: "Type your message"
            size_hint: 0.8, None  # Make it take 80% of the available space horizontally
            height: "40dp" 

        MDRaisedButton:
            text: "Send" 
            size_hint: 0.2, None  # Make it take 80% of the available space horizontally
            height: "40dp" 
            on_release: app.add_to_list()

    MDScrollView:
        MDList:
            id: mylist
"""

class Application(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV)

    # def on_start(self):
    #     # Start receiving messages when the app begins
    #     self.receive_message()

    def add_to_list(self):
        # Get the text from the text field
        text = self.root.ids.text_field.text
        if text:  # Only add if the text field is not empty
            # Add a new OneLineListItem to the MDList
            self.root.ids.mylist.add_widget(
                OneLineListItem(text=text)
            )
            self.send_message(text)  # Send the message
            # Clear the text field after adding
            self.root.ids.text_field.text = ""

    def on_microphone_button_pressed(self):
        """
        This method will be called when the microphone button is pressed.
        You can start recording or any other desired action here.
        """
        print("Microphone button pressed!")
        # Add your functionality here, like starting recording
        # For example, let's call the `receive_message` to start listening for incoming FSK signals
        self.receive_message()

    #-------------------sender code ------------
    # Convert text to binary (UTF-8 encoded)
    def text_to_bin(self, text):
        return ''.join(format(ord(c), '08b') for c in text)

    # Modulate the binary data into FSK
    def fsk_modulate(self, binary_data):
        signal_data = []
        
        for bit in binary_data:
            if bit == '0':
                freq = f1
            else:
                freq = f2
            
            t = np.linspace(0, duration_per_bit, int(fs * duration_per_bit), endpoint=False)
            modulated_signal = np.sin(2 * np.pi * freq * t)
            signal_data.append(modulated_signal)
        
        return np.concatenate(signal_data)

    # Send the modulated signal through speakers
    def send_message(self, message):
        binary_message = self.text_to_bin(message)  # Convert message to binary
        modulated_signal = self.fsk_modulate(binary_message)  # FSK Modulation

        # Play the modulated signal
        print(f"Sending message: {message}")
        sd.play(modulated_signal, fs)  # Play sound
        sd.wait()  # Wait until the sound finishes playing

    #-------------------receiver code ------------
    # Demodulate FSK to binary data
    def fsk_demodulate(self, signal_data):
        decoded_bits = []
        num_samples_per_bit = int(fs * duration_per_bit)
        
        for i in range(0, len(signal_data), num_samples_per_bit):
            segment = signal_data[i:i+num_samples_per_bit]
            fft_result = np.fft.fft(segment)
            freqs = np.fft.fftfreq(len(segment), 1/fs)
            peak_freq = np.abs(freqs[np.argmax(np.abs(fft_result))])
            
            # Check if the frequency is within expected range for bit 0 or bit 1
            if peak_freq < (f1 + f2) / 2:  # Bit 0
                decoded_bits.append('0')
            else:  # Bit 1
                decoded_bits.append('1')
        
        return ''.join(decoded_bits)

    # Convert binary data back to text
    def bin_to_text(self, binary_data):
        text = ""
        for i in range(0, len(binary_data), 8):
            byte = binary_data[i:i+8]
            text += chr(int(byte, 2))
        return text

    # Check for valid message by comparing to known valid characters
    def is_valid_message(self, decoded_message):
        # We assume a valid message contains printable ASCII characters only
        return all(32 <= ord(c) <= 126 for c in decoded_message)

    # Record and demodulate the received signal
    def receive_message(self):
        print("Waiting for message...")

        # Record audio from the microphone (adjust duration as needed)
        duration = 5  # Adjust based on the expected message duration
        recorded_signal = sd.rec(int(fs * duration), samplerate=fs, channels=1, dtype='float64')
        sd.wait()  # Wait until recording is complete

        # Demodulate the received signal
        decoded_binary = self.fsk_demodulate(recorded_signal.flatten())  # Flatten in case of stereo recording
        decoded_message = self.bin_to_text(decoded_binary)

        # Check if the decoded message is valid
        if self.is_valid_message(decoded_message):
            if decoded_message:  # Only add if the text field is not empty
                # Add a new OneLineListItem to the MDList
                self.root.ids.mylist.add_widget(
                    OneLineListItem(text=decoded_message)
                )
        else:
            print("Decoded message contains invalid characters. Skipping...")

Application().run()
