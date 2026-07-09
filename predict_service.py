from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
from ultralytics import YOLO
import os
import torch

app = Flask(__name__)
torch.set_num_threads(1)

# Carrega o seu modelo YOLO (verifique se o nome do arquivo .pt está correto)
model = YOLO('modelo_yolo_libras.pt')

@app.route('/predict', methods=['POST'])
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if 'image' not in data:
            return jsonify({'error': 'Nenhuma imagem fornecida'}), 400

        base64_img = data['image']
        w = data.get('width')
        h = data.get('height')
        stride = data.get('stride')

        img_data = base64.b64decode(base64_img)
        np_arr = np.frombuffer(img_data, np.uint8)

        # MONTANDO O QUEBRA-CABEÇA DE PIXELS
        try:
            img = np_arr.reshape((h, stride)) 
            img = img[:, :w] 
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            img = cv2.flip(img, 1) # Espelha a imagem]
        except Exception as e:
            return jsonify({'error': f'Erro ao remontar pixels: {str(e)}'}), 400

        # Passa pro modelo
        results = model.predict(source=img, imgsz=320, conf=0.5, verbose=False)
        
        prediction = "Nenhum"
        confidence = 0.0
        
        if len(results) > 0 and len(results[0].boxes) > 0:
            box = results[0].boxes[0]
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            prediction = model.names[class_id]

        return jsonify({
            'prediction': prediction,
            'confidence': confidence
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # O Render injeta a porta na variável de ambiente PORT. O padrão local fica 5000.
    port = int(os.environ.get("PORT", 5000))    
    # O host 0.0.0.0 é obrigatório para servidores em nuvem
    app.run(host='0.0.0.0', port=port)