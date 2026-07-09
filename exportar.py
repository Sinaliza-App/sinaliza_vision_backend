from ultralytics import YOLO

# 1. Carrega o seu modelo PyTorch treinado
model = YOLO('modelo_yolo_libras.pt')

# 2. Exporta o modelo para o formato otimizado ONNX
model.export(format='onnx')