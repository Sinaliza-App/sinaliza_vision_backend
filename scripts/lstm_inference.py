import os
import json
import numpy as np
import torch
import torch.nn as nn
from collections import deque

class ClassificadorLSTMLibras(nn.Module):
    """
    Arquitetura de rede neural recorrente (LSTM) para classificação de sinais dinâmicos de Libras.
    Mantém-se idêntica à arquitetura original para garantir compatibilidade de pesos.
    """
    def __init__(self, input_size, hidden_size, num_classes):
        super(ClassificadorLSTMLibras, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = 2
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers=self.num_layers, 
            batch_first=True, 
            dropout=0.3
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


def carregar_mapeamento_classes(class_map_path):
    """
    Carrega o mapa de classes a partir de um arquivo JSON persistente.
    Retorna uma lista ordenada das classes com base nas chaves numéricas do JSON.
    """
    if not os.path.exists(class_map_path):
        raise FileNotFoundError(f"[ERRO] O mapa de classes '{class_map_path}' não foi encontrado.")
        
    with open(class_map_path, 'r', encoding='utf-8') as f:
        class_map = json.load(f)
        
    # Ordena as chaves numéricas para garantir que a lista de classes tenha a ordem correta
    classes = [class_map[str(i)] for i in range(len(class_map))]
    return classes


class LSTMInferenceManager:
    """
    Classe de alto nível para gerenciar o pipeline de inferência LSTM.
    Responsável pelo carregamento do modelo, execução de predições em lote ou frame a frame,
    e suavização temporal das predições para evitar oscilações em tempo real.
    """
    def __init__(self, model_path, class_map_path, num_frames=30, input_size=258, confidence_threshold=0.55, device=None):
        self.num_frames = num_frames
        self.input_size = input_size
        self.confidence_threshold = confidence_threshold
        
        # Define o dispositivo de inferência
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device
            
        # Carrega o mapeamento de classes
        self.classes = carregar_mapeamento_classes(class_map_path)
        self.num_classes = len(self.classes)
        
        # Inicializa o modelo
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"[ERRO] O arquivo de pesos do modelo '{model_path}' não foi encontrado.")
            
        state_dict = torch.load(model_path, map_location=self.device)
        checkpoint_classes = state_dict['fc.3.bias'].shape[0]
        
        if self.num_classes != checkpoint_classes:
            raise ValueError(
                f"[ERRO] Incompatibilidade de classes! O modelo em '{model_path}' espera {checkpoint_classes} classes, "
                f"mas o class_map_lstm contém {self.num_classes} classes mapeadas."
            )
            
        self.model = ClassificadorLSTMLibras(self.input_size, 128, self.num_classes).to(self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()
        
        # Buffer de frames e histórico para suavização (tempo real)
        self.sequence = []
        self.historico_predicoes = deque(maxlen=5)
        
    def predict_sequence(self, sequence_np):
        """
        Realiza a inferência em uma sequência completa de 30 frames.
        Retorna (sinal_predito, valor_confianca)
        """
        # Validação do formato de entrada
        if len(sequence_np.shape) != 2 or sequence_np.shape != (self.num_frames, self.input_size):
            raise ValueError(f"Formato incorreto de entrada para predict_sequence. Esperado ({self.num_frames}, {self.input_size}), obtido {sequence_np.shape}")
            
        if np.isnan(sequence_np).any():
            raise ValueError("Valores NaN detectados na sequência de entrada para inferência")
            
        # Converte para PyTorch Tensor e adiciona dimensão de lote (1, 30, input_size)
        input_tensor = torch.from_numpy(sequence_np.astype(np.float32)).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confianca, pred_idx = torch.max(probabilities, 1)
            
        sinal_predito = self.classes[pred_idx.item()]
        valor_confianca = confianca.item()
        
        return sinal_predito, valor_confianca

    def predict_frame(self, keypoints_norm):
        """
        Recebe as coordenadas normalizadas de um único frame, gerencia a fila temporal e a suavização.
        Retorna (sinal_atual, confianca_atual)
        """
        if keypoints_norm.shape[0] != self.input_size:
            raise ValueError(f"Tamanho de características incorreto no frame. Esperado {self.input_size}, obtido {keypoints_norm.shape[0]}")
            
        if np.isnan(keypoints_norm).any():
            raise ValueError("Valores NaN detectados no frame de entrada")
            
        # Adiciona o frame ao buffer temporal
        self.sequence.append(keypoints_norm)
        self.sequence = self.sequence[-self.num_frames:]
        
        # Se ainda não temos frames suficientes, retorna estado inicial
        if len(self.sequence) < self.num_frames:
            return "Detectando...", 0.0
            
        # Executa inferência sobre o buffer de 30 frames
        sequence_np = np.array(self.sequence, dtype=np.float32)
        sinal_predito, valor_confianca = self.predict_sequence(sequence_np)
        
        # Filtro de confiança mínima para suavização temporal
        if valor_confianca >= self.confidence_threshold:
            self.historico_predicoes.append(sinal_predito)
        else:
            self.historico_predicoes.append("Aguardando...")
            
        # Votação majoritária no histórico de predições recentes
        sinal_mais_votado = max(set(self.historico_predicoes), key=self.historico_predicoes.count)
        
        if sinal_mais_votado != "Aguardando...":
            sinal_atual = sinal_mais_votado
            confianca_atual = valor_confianca
        else:
            sinal_atual = "Aguardando..."
            confianca_atual = 0.0
            
        return sinal_atual, confianca_atual
