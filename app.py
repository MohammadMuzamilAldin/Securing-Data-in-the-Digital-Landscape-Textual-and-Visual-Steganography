from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename  # Import secure_filename

from PIL import Image
import os
import io
from io import BytesIO
import cv2
import numpy as np
import pandas as pand
from matplotlib import pyplot as plt




app = Flask(__name__)
app.secret_key = '1'

class Stegno:
    def genData(self, data):
        newd = []

        for i in data:
            newd.append(format(ord(i), '08b'))
        return newd

    def modPix(self, pix, data):
        datalist = self.genData(data)
        lendata = len(datalist)
        imdata = iter(pix)
        for i in range(lendata):
            # Extracting 3 pixels at a time
            pix = [value for value in imdata.__next__()[:3] +
                   imdata.__next__()[:3] +
                   imdata.__next__()[:3]]
            # Pixel value should be made
            # odd for 1 and even for 0
            for j in range(0, 8):
                if (datalist[i][j] == '0') and (pix[j] % 2 != 0):

                    if (pix[j] % 2 != 0):
                        pix[j] -= 1

                elif (datalist[i][j] == '1') and (pix[j] % 2 == 0):
                    pix[j] -= 1
            # Eighth pixel of every set tells
            # whether to stop or read further.
            # 0 means keep reading; 1 means the
            # message is over.
            if (i == lendata - 1):
                if (pix[-1] % 2 == 0):
                    pix[-1] -= 1
            else:
                if (pix[-1] % 2 != 0):
                    pix[-1] -= 1

            pix = tuple(pix)
            yield pix[0:3]
            yield pix[3:6]
            yield pix[6:9]

    def encode_enc(self, newimg, data):
        w = newimg.size[0]
        (x, y) = (0, 0)

        for pixel in self.modPix(newimg.getdata(), data):
            # Putting modified pixels in the new image
            newimg.putpixel((x, y), pixel)
            if (x == w - 1):
                x = 0
                y += 1
            else:
                x += 1

    def encode_text_into_image(self, image_file, text_data):
        image = Image.open(image_file)
        new_image = image.copy()
        self.encode_enc(new_image, text_data)
        return new_image

    def decode(self, image_path):
        data = ''
        img = Image.open(image_path)
        imgdata = iter(img.getdata())

        while True:
            pixels = [value for value in imgdata.__next__()[:3] +
                      imgdata.__next__()[:3] +
                      imgdata.__next__()[:3]]
            binstr = ''
            for i in pixels[:8]:
                if i % 2 == 0:
                    binstr += '0'
                else:
                    binstr += '1'

            data += chr(int(binstr, 2))
            if pixels[-1] % 2 != 0:
                return data



    #auidio
    def encode_aud_data(self, file_name, data, stegofile):
        import wave

        song = wave.open(file_name, mode='rb')
        nframes = song.getnframes()
        frames = song.readframes(nframes)
        frame_list = list(frames)
        frame_bytes = bytearray(frame_list)
        data += '*^*^*'
        result = []
        for c in data:
            bits = bin(ord(c))[2:].zfill(8)
            result.extend([int(b) for b in bits])

        j = 0
        for i in range(0, len(result), 1):
            res = bin(frame_bytes[j])[2:].zfill(8)
            if res[len(res) - 4] == result[i]:
                frame_bytes[j] = (frame_bytes[j] & 253)      # 253: 11111101
            else:
                frame_bytes[j] = (frame_bytes[j] & 253) | 2
                frame_bytes[j] = (frame_bytes[j] & 254) | result[i]
            j += 1

        frame_modified = bytes(frame_bytes)

        with wave.open(stegofile, 'wb') as fd:
            fd.setparams(song.getparams())
            fd.writeframes(frame_modified)
        song.close()

    def decode_aud_data(self, file_name):
        import wave

        song = wave.open(file_name, mode='rb')
        nframes = song.getnframes()
        frames = song.readframes(nframes)
        frame_list = list(frames)
        frame_bytes = bytearray(frame_list)
        extracted = ""
        p = 0
        for i in range(len(frame_bytes)):
            if p == 1:
                break
            res = bin(frame_bytes[i])[2:].zfill(8)
            if res[len(res) - 2] == '0':
                extracted += res[len(res) - 4]
            else:
                extracted += res[len(res) - 1]

        all_bytes = [extracted[i: i + 8] for i in range(0, len(extracted), 8)]
        decoded_data = ""
        for byte in all_bytes:
            decoded_data += chr(int(byte, 2))
            if decoded_data[-5:] == "*^*^*":
                p = 1
                break
        song.close()
        return decoded_data[:-5]
            #audio above
   
stegno = Stegno()

@app.route('/')
def index():
    return render_template('index.html')

# Route to handle index page
@app.route('/das', methods=['GET', 'POST'])
def das():
    if request.method == 'POST':
        if 'encode' in request.form:
            text_data = request.form['text_data']
            image_file = request.files['image_file']

            if text_data and image_file:
                # Save the uploaded image temporarily
                image_path = '/Users/mohammadmuzamilaldin/Desktop/MajorP/uploads/' + image_file.filename
                image_file.save(image_path)

                # Perform encoding
                encoded_image = stegno.encode_text_into_image(image_path, text_data)

                # Save the encoded image
                encoded_image_path = 'encrypted images/' + os.path.splitext(image_file.filename)[0] + '_encoded.png'
                encoded_image.save(encoded_image_path)

                # Send the encoded image file for download
                return send_file(encoded_image_path, as_attachment=True)
        
        elif 'decode' in request.form:
            encrypted_image = request.files['encrypted_image']

            if encrypted_image:
                decoded_text = stegno.decode(encrypted_image)
                return render_template('das.html', decoded_text=decoded_text)
    
    return render_template('das.html')

# Route to handle other pages


#audio


@app.route('/audio_steganography', methods=['GET', 'POST'])
def audio_steganography():
    if request.method == 'POST':
        if 'audio_encrypt' in request.form:
            # Handle audio encryption form submission
            audio_file = request.files['audio_file']
            text_data = request.form['text_data']
            stegofile = '/Users/mohammadmuzamilaldin/Desktop/MajorP/uploads/audio.wav'
            stegno.encode_aud_data(audio_file, text_data, stegofile)
            return "Audio encryption successful."
        elif 'audio_decrypt' in request.form:
            # Handle audio decryption form submission
            encrypted_audio = request.files['encrypted_audio']
            decoded_text = stegno.decode_aud_data(encrypted_audio)
            return render_template('audio_steganography.html', decoded_text=decoded_text)
    # Render the audio steganography HTML template
    return render_template('audio_steganography.html')

#above audio


@app.route('/dashboard.html')
def dashboard():
    return render_template('dashboard.html')

@app.route('/encrypt.html')
def encrypt():
    return render_template('encrypt.html')

@app.route('/decrypt.html')
def decrypt():
    return render_template('decrypt.html')



if __name__ == '__main__':
    app.run(debug=True, port=5001)

