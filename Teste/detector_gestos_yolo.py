"""
Detector de Gestos Libras usando YOLO
Usa o modelo YOLO treinado para detecção em tempo real
"""

import cv2
import os
import time
import numpy as np
from collections import deque, Counter

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Erro: ultralytics não instalado!")
    print("Instale com: pip install ultralytics")
    exit(1)

class DetectorLibrasYOLO:
    """Detector de gestos Libras usando YOLO."""
    
    def __init__(self, modelo_path=None):
        """
        Inicializa o detector com o modelo YOLO treinado.
        
        Args:
            modelo_path: Caminho para o modelo YOLO (.pt)
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Procurar modelo
        if modelo_path is None:
            # Tentar encontrar modelo treinado
            possibilidades = [
                os.path.join(base_dir, 'modelo_yolo_libras.pt'),
                os.path.join(base_dir, 'runs', 'libras', 'train', 'weights', 'best.pt'),
                os.path.join(base_dir, 'best.pt')
            ]
            
            for path in possibilidades:
                if os.path.exists(path):
                    modelo_path = path
                    break
        
        if modelo_path is None or not os.path.exists(modelo_path):
            print("❌ Modelo YOLO não encontrado!")
            print("\nPara treinar o modelo, execute:")
            print("  python treinar_yolo.py")
            print("\nOu coloque o arquivo 'modelo_yolo_libras.pt' neste diretório")
            self.carregado = False
            return
        
        self.modelo_path = modelo_path
        self.modelo = None
        self.carregado = False
        
        # Histórico para suavização
        self.historico_deteccoes = deque(maxlen=10)
        self.ultimo_gesto = ""
        self.tempo_ultimo_gesto = 0
        self.confianca_minima = 0.5
        
        # Carregar modelo
        self.carregar_modelo()
    
    def carregar_modelo(self):
        """Carrega o modelo YOLO."""
        try:
            print(f"📦 Carregando modelo YOLO: {self.modelo_path}")
            self.modelo = YOLO(self.modelo_path)
            self.carregado = True
            print("✓ Modelo YOLO carregado com sucesso!")
            
            # Mostrar classes
            if hasattr(self.modelo, 'names'):
                print(f"✓ Classes: {list(self.modelo.names.values())}")
            
        except Exception as e:
            print(f"❌ Erro ao carregar modelo: {e}")
            self.carregado = False
    
    def detectar(self, image):
        """
        Detecta gestos na imagem.
        
        Args:
            image: Imagem BGR do OpenCV
            
        Returns:
            Lista de detecções [(classe, confianca, bbox), ...]
        """
        if not self.carregado:
            return []
        
        # Fazer predição
        results = self.modelo(image, verbose=False)
        
        deteccoes = []
        
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                # Extrair informações
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                if conf >= self.confianca_minima:
                    classe_nome = self.modelo.names[cls]
                    deteccoes.append((classe_nome, conf, bbox))
        
        return deteccoes
    
    def gesto_suavizado(self, deteccoes):
        """
        Aplica suavização temporal nas detecções.
        
        Args:
            deteccoes: Lista de detecções da frame atual
            
        Returns:
            Melhor detecção suavizada ou None
        """
        if not deteccoes:
            return None
        
        # Adicionar melhor detecção ao histórico
        melhor = max(deteccoes, key=lambda x: x[1])
        self.historico_deteccoes.append(melhor[0])
        
        # Verificar consenso no histórico
        if len(self.historico_deteccoes) >= 5:
            contador = Counter(self.historico_deteccoes)
            classe_comum, freq = contador.most_common(1)[0]
            
            # Se a classe aparece em pelo menos 60% das detecções
            if freq / len(self.historico_deteccoes) >= 0.6:
                return melhor  # Retorna com confiança e bbox
        
        return None

def main():
    """Função principal para executar o detector YOLO."""
    
    # Criar detector
    detector = DetectorLibrasYOLO()
    
    if not detector.carregado:
        print("\n❌ Impossível iniciar sem modelo YOLO treinado!")
        return
    
    # Captura de vídeo
    cap = cv2.VideoCapture(0)
    
    # Configuração da janela
    window_name = "Sinaliza App - Detector YOLO Libras"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # Variáveis de controle
    ultimo_texto = ""
    tempo_texto = 0
    fps_counter = deque(maxlen=30)
    last_time = time.time()
    
    print("\n" + "="*70)
    print("🎥 DETECTOR YOLO DE LIBRAS INICIADO")
    print("="*70)
    print("Pressione ESC para sair")
    print("="*70 + "\n")
    
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("⚠ Não foi possível capturar a imagem da câmera.")
            continue
        
        # Espelhar imagem
        image = cv2.flip(image, 1)
        h, w, _ = image.shape
        
        # Calcular FPS
        current_time = time.time()
        fps = 1.0 / (current_time - last_time)
        last_time = current_time
        fps_counter.append(fps)
        avg_fps = np.mean(fps_counter)
        
        # Detectar gestos
        deteccoes = detector.detectar(image)
        
        # Aplicar suavização
        melhor_deteccao = detector.gesto_suavizado(deteccoes)
        
        # Desenhar detecções
        for classe, conf, bbox in deteccoes:
            x1, y1, x2, y2 = map(int, bbox)
            
            # Caixa delimitadora
            cor = (0, 255, 0) if conf > 0.7 else (0, 255, 255)
            cv2.rectangle(image, (x1, y1), (x2, y2), cor, 2)
            
            # Label
            label = f"{classe} {conf*100:.1f}%"
            (label_width, label_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            # Fundo do label
            cv2.rectangle(image, (x1, y1 - label_height - 10),
                         (x1 + label_width, y1), cor, -1)
            
            # Texto do label
            cv2.putText(image, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Atualizar texto principal
        if melhor_deteccao:
            ultimo_texto = melhor_deteccao[0]
            tempo_texto = time.time()
            confianca = melhor_deteccao[1]
        
        # Overlay superior
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
        
        # FPS
        cv2.putText(image, f"FPS: {avg_fps:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Status do modelo
        cv2.putText(image, "Modelo: YOLO", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Número de detecções
        cv2.putText(image, f"Deteccoes: {len(deteccoes)}", (w - 200, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Exibir gesto principal (mantém por 2 segundos)
        if time.time() - tempo_texto < 2 and ultimo_texto:
            texto = ultimo_texto
            font_scale = 3
            thickness = 5
            (text_width, text_height), baseline = cv2.getTextSize(
                texto, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )
            
            # Centralizar
            x = (w - text_width) // 2
            y = (h + text_height) // 2
            
            # Fundo
            overlay = image.copy()
            padding = 20
            cv2.rectangle(overlay,
                        (x - padding, y - text_height - padding),
                        (x + text_width + padding, y + padding),
                        (0, 255, 0), -1)
            image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
            
            # Texto
            cv2.putText(image, texto, (x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255),
                       thickness, cv2.LINE_AA)
            
            # Confiança
            if melhor_deteccao:
                conf_text = f"Confianca: {confianca*100:.1f}%"
                cv2.putText(image, conf_text, (x, y + 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255),
                           2, cv2.LINE_AA)
        
        # Instruções
        cv2.putText(image, "Pressione ESC para sair", (w - 300, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Mostrar imagem
        cv2.imshow(window_name, image)
        
        # Verificar teclas
        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n✓ Detector encerrado")

if __name__ == "__main__":
    main()

