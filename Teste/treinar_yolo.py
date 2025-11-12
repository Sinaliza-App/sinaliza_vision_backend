"""
Script para treinar um modelo YOLO para detecção de gestos Libras.
Este script usa o dataset já anotado em formato YOLO.
"""

from ultralytics import YOLO
import os
import torch

def verificar_dataset():
    """Verifica se o dataset está configurado corretamente."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_yaml = os.path.join(base_dir, 'data.yaml')
    
    if not os.path.exists(data_yaml):
        print(f"❌ Erro: Arquivo {data_yaml} não encontrado!")
        return False
    
    print("✓ Arquivo data.yaml encontrado")
    
    # Verificar diretórios
    dirs = ['train/images', 'valid/images', 'test/images']
    for d in dirs:
        path = os.path.join(base_dir, d)
        if os.path.exists(path):
            num_files = len([f for f in os.listdir(path) if f.endswith('.jpg')])
            print(f"✓ {d}: {num_files} imagens")
        else:
            print(f"⚠ {d}: não encontrado")
    
    return True

def treinar_yolo(epochs=50, img_size=640, batch_size=16, modelo_base='yolov8n.pt'):
    """
    Treina o modelo YOLO.
    
    Args:
        epochs: Número de épocas de treinamento
        img_size: Tamanho da imagem
        batch_size: Tamanho do batch
        modelo_base: Modelo base do YOLO (n=nano, s=small, m=medium, l=large, x=xlarge)
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_yaml = os.path.join(base_dir, 'data.yaml')
    
    print("="*70)
    print("TREINAMENTO YOLO PARA DETECÇÃO DE LIBRAS")
    print("="*70)
    
    # Verificar GPU
    if torch.cuda.is_available():
        print(f"✓ GPU disponível: {torch.cuda.get_device_name(0)}")
        device = 0
    else:
        print("⚠ GPU não disponível, usando CPU (mais lento)")
        device = 'cpu'
    
    # Carregar modelo base
    print(f"\n📦 Carregando modelo base: {modelo_base}")
    model = YOLO(modelo_base)
    
    # Treinar
    print(f"\n🚀 Iniciando treinamento...")
    print(f"   - Épocas: {epochs}")
    print(f"   - Tamanho da imagem: {img_size}")
    print(f"   - Batch size: {batch_size}")
    print(f"   - Device: {device}")
    
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        device=device,
        patience=20,  # Early stopping
        save=True,
        project='runs/libras',
        name='train',
        exist_ok=True,
        pretrained=True,
        optimizer='auto',
        verbose=True,
        seed=42,
        deterministic=True,
        single_cls=False,
        rect=False,
        cos_lr=False,
        close_mosaic=10,
        resume=False,
        amp=True,
        fraction=1.0,
        profile=False,
        freeze=None,
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        pose=12.0,
        kobj=2.0,
        label_smoothing=0.0,
        nbs=64,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0
    )
    
    print("\n" + "="*70)
    print("✅ TREINAMENTO CONCLUÍDO!")
    print("="*70)
    
    # Validar modelo
    print("\n📊 Validando modelo...")
    metrics = model.val()
    
    print(f"\n📈 Métricas de Validação:")
    print(f"   - mAP50: {metrics.box.map50:.4f}")
    print(f"   - mAP50-95: {metrics.box.map:.4f}")
    print(f"   - Precision: {metrics.box.mp:.4f}")
    print(f"   - Recall: {metrics.box.mr:.4f}")
    
    # Salvar modelo final
    model_path = os.path.join(base_dir, 'modelo_yolo_libras.pt')
    model.save(model_path)
    print(f"\n💾 Modelo salvo em: {model_path}")
    
    # Exportar para outros formatos (opcional)
    print("\n📤 Exportando modelo...")
    try:
        model.export(format='onnx')
        print("✓ Modelo exportado para ONNX")
    except Exception as e:
        print(f"⚠ Erro ao exportar: {e}")
    
    return model, results

def testar_modelo(modelo_path=None):
    """Testa o modelo treinado com o conjunto de teste."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if modelo_path is None:
        # Procurar o modelo mais recente
        runs_dir = os.path.join(base_dir, 'runs', 'libras', 'train')
        if os.path.exists(runs_dir):
            weights_path = os.path.join(runs_dir, 'weights', 'best.pt')
            if os.path.exists(weights_path):
                modelo_path = weights_path
            else:
                print("❌ Modelo treinado não encontrado!")
                return
    
    print("\n" + "="*70)
    print("TESTANDO MODELO")
    print("="*70)
    
    model = YOLO(modelo_path)
    
    # Testar no conjunto de teste
    data_yaml = os.path.join(base_dir, 'data.yaml')
    metrics = model.val(data=data_yaml, split='test')
    
    print(f"\n📊 Métricas de Teste:")
    print(f"   - mAP50: {metrics.box.map50:.4f}")
    print(f"   - mAP50-95: {metrics.box.map:.4f}")
    print(f"   - Precision: {metrics.box.mp:.4f}")
    print(f"   - Recall: {metrics.box.mr:.4f}")

def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Treinar YOLO para Libras')
    parser.add_argument('--epochs', type=int, default=50, help='Número de épocas (padrão: 50)')
    parser.add_argument('--img-size', type=int, default=640, help='Tamanho da imagem (padrão: 640)')
    parser.add_argument('--batch-size', type=int, default=16, help='Tamanho do batch (padrão: 16)')
    parser.add_argument('--model', type=str, default='yolov8n.pt', 
                       help='Modelo base: yolov8n.pt (nano/rápido), yolov8s.pt (small), yolov8m.pt (médio)')
    parser.add_argument('--test-only', action='store_true', 
                       help='Apenas testar modelo existente')
    
    args = parser.parse_args()
    
    if not verificar_dataset():
        return
    
    if args.test_only:
        testar_modelo()
    else:
        model, results = treinar_yolo(
            epochs=args.epochs,
            img_size=args.img_size,
            batch_size=args.batch_size,
            modelo_base=args.model
        )
        
        # Testar após treino
        testar_modelo()

if __name__ == "__main__":
    main()

