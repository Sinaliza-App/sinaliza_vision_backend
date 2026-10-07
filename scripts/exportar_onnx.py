import os
import sys
import json
import shutil
import numpy as np

# Força codificação UTF-8 no stdout do Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import torch
import torch.nn as nn
import onnx
import onnxruntime as ort
from lstm_inference import ClassificadorLSTMLibras

# =====================================================================
# DEFINICAO DO CLASSIFICADOR MLP DO ALFABETO
# =====================================================================
class ClassificadorMLPAlfabeto(nn.Module):
    def __init__(self, input_size=258, hidden_size=128, num_classes=27):
        super(ClassificadorMLPAlfabeto, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )
        
    def forward(self, x):
        return self.network(x)

def exportar_alfabeto():
    print("\n" + "="*60)
    print("[EXPORT] MODELO MLP DO ALFABETO (ESTATICO) -> ONNX")
    print("="*60)
    
    pth_path = 'modelo_mlp_alfabeto.pth'
    json_path = 'class_map_alfabeto.json'
    onnx_path = 'modelo_mlp_alfabeto.onnx'
    
    if not os.path.exists(pth_path) or not os.path.exists(json_path):
        print(f"[AVISO] Arquivos '{pth_path}' ou '{json_path}' nao encontrados. Pulando alfabeto.")
        return None
        
    with open(json_path, 'r', encoding='utf-8') as f:
        class_map = json.load(f)
    num_classes = len(class_map)
    
    # Carregar modelo PyTorch
    state_dict = torch.load(pth_path, map_location='cpu')
    actual_classes = state_dict['network.6.bias'].shape[0] if 'network.6.bias' in state_dict else num_classes
    
    model = ClassificadorMLPAlfabeto(input_size=258, hidden_size=128, num_classes=actual_classes)
    model.load_state_dict(state_dict)
    model.eval()
    
    # Tensor dummy para exportação: (batch_size=1, features=258)
    dummy_input = torch.randn(1, 258, dtype=torch.float32)
    
    # Exportar para ONNX usando o exporter clássico (dynamo=False)
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        },
        dynamo=False
    )
    
    # Validar grafo ONNX
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    print(f"[OK] Grafo ONNX verificado com sucesso: '{onnx_path}' ({os.path.getsize(onnx_path) / 1024:.1f} KB)")
    
    # Validar equivalência numérica PyTorch vs ONNX Runtime
    ort_session = ort.InferenceSession(onnx_path)
    with torch.no_grad():
        py_out = model(dummy_input).numpy()
        
    ort_inputs = {ort_session.get_inputs()[0].name: dummy_input.numpy()}
    ort_out = ort_session.run(None, ort_inputs)[0]
    
    diff = np.max(np.abs(py_out - ort_out))
    print(f"[OK] Validacao Numerica (PyTorch vs ONNX Runtime): Diferenca maxima = {diff:.2e}")
    assert diff < 1e-4, "Erro: Diferenca numerica excessiva entre PyTorch e ONNX!"
    
    return onnx_path

def exportar_lstm():
    print("\n" + "="*60)
    print("[EXPORT] MODELO LSTM DE EXPRESSOES DINAMICAS -> ONNX")
    print("="*60)
    
    pth_path = 'modelo_lstm_libras.pth'
    json_path = 'class_map_lstm.json'
    onnx_path = 'modelo_lstm_libras.onnx'
    
    if not os.path.exists(pth_path) or not os.path.exists(json_path):
        print(f"[ERRO] Arquivos '{pth_path}' ou '{json_path}' nao encontrados.")
        return None
        
    with open(json_path, 'r', encoding='utf-8') as f:
        class_map = json.load(f)
    num_classes = len(class_map)
    
    # Carregar modelo PyTorch
    state_dict = torch.load(pth_path, map_location='cpu')
    actual_classes = state_dict['fc.3.bias'].shape[0] if 'fc.3.bias' in state_dict else num_classes
    
    model = ClassificadorLSTMLibras(input_size=258, hidden_size=128, num_classes=actual_classes)
    model.load_state_dict(state_dict)
    model.eval()
    
    # Tensor dummy para exportação: (batch_size=1, frames=30, features=258)
    dummy_input = torch.randn(1, 30, 258, dtype=torch.float32)
    
    # Exportar para ONNX usando o exporter clássico (dynamo=False)
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        },
        dynamo=False
    )
    
    # Validar grafo ONNX
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    print(f"[OK] Grafo ONNX verificado com sucesso: '{onnx_path}' ({os.path.getsize(onnx_path) / 1024:.1f} KB)")
    
    # Validar equivalência numérica PyTorch vs ONNX Runtime
    ort_session = ort.InferenceSession(onnx_path)
    with torch.no_grad():
        py_out = model(dummy_input).numpy()
        
    ort_inputs = {ort_session.get_inputs()[0].name: dummy_input.numpy()}
    ort_out = ort_session.run(None, ort_inputs)[0]
    
    diff = np.max(np.abs(py_out - ort_out))
    print(f"[OK] Validacao Numerica (PyTorch vs ONNX Runtime): Diferenca maxima = {diff:.2e}")
    assert diff < 1e-4, "Erro: Diferenca numerica excessiva entre PyTorch e ONNX!"
    
    return onnx_path

def sincronizar_com_app_flutter():
    print("\n" + "="*60)
    print("[SINCRONIZACAO] MODELOS ONNX -> APP FLUTTER (assets/models)")
    print("="*60)
    
    app_assets_dir = os.path.join('sinaliza_app_libras', 'assets', 'models')
    os.makedirs(app_assets_dir, exist_ok=True)
    
    arquivos_para_copiar = [
        'modelo_mlp_alfabeto.onnx',
        'class_map_alfabeto.json',
        'modelo_lstm_libras.onnx',
        'class_map_lstm.json'
    ]
    
    for f in arquivos_para_copiar:
        if os.path.exists(f):
            dest = os.path.join(app_assets_dir, f)
            shutil.copy2(f, dest)
            print(f"[OK] Copiado: {f} -> {dest}")
        else:
            print(f"[AVISO] Arquivo {f} nao encontrado na raiz para copia.")

if __name__ == '__main__':
    print("[INFO] INICIANDO PIPELINE DE EXPORTACAO UNIVERSAL ONNX")
    exportar_alfabeto()
    exportar_lstm()
    sincronizar_com_app_flutter()
    print("\n[SUCESSO] TODOS OS MODELOS FORAM EXPORTADOS E SINCRONIZADOS!")
