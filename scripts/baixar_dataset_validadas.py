"""
Sinaliza App - Sincronizador de Amostras Validadas para Treino (MLOps)
Baixa as amostras validadas pelo professor no Web Dashboard e salva como .npy
na pasta do dataset para retreinamento com `treinar_lstm.py` ou `treinar_alfabeto.py`.
"""

import os
import sys
import json
import argparse
import requests
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "treinamento")

def sincronizar_dataset(api_url="https://sinaliza-api-cn07.onrender.com", token=None, target_version="v2", json_file=None):
    target_dir = os.path.join(DATASET_DIR, target_version)
    os.makedirs(target_dir, exist_ok=True)

    samples = []

    # 1. Obter dados via arquivo exportado ou via requisição HTTP
    if json_file and os.path.exists(json_file):
        print(f"[INFO] Lendo manifesto do dataset do arquivo local: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            samples = data.get("samples", [])
    else:
        endpoint = f"{api_url.rstrip('/')}/coleta/exportar-manifesto"
        print(f"[INFO] Baixando manifesto de amostras validadas de: {endpoint}")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            res = requests.get(endpoint, headers=headers, timeout=30)
            res.raise_for_status()
            data = res.json()
            samples = data.get("samples", [])
        except Exception as e:
            print(f"[ERRO] Falha ao baixar manifesto via API: {e}")
            print("[DICA] Se exportou pelo Web Dashboard, passe o arquivo com --file caminho.json")
            return

    if not samples:
        print("[AVISO] Nenhuma amostra validada encontrada para sincronizar.")
        return

    print(f"[INFO] Processando {len(samples)} amostras validadas para a pasta '{target_version}'...")

    salvos_count = 0
    for s in samples:
        sign_name = s.get("sign_name")
        raw_landmarks = s.get("raw_landmarks")
        sample_id = s.get("id")

        if not sign_name or not raw_landmarks:
            continue

        class_dir = os.path.join(target_dir, sign_name.lower().strip())
        os.makedirs(class_dir, exist_ok=True)

        arr = np.array(raw_landmarks, dtype=np.float32)
        out_path = os.path.join(class_dir, f"video_{sample_id}.npy")

        try:
            np.save(out_path, arr)
            salvos_count += 1
        except Exception as e:
            print(f"[ERRO] Falha ao salvar {out_path}: {e}")

    print(f"\n✅ Sincronização concluída com sucesso! {salvos_count} arquivos .npy gerados em '{target_dir}'.")
    print(f"🚀 Para treinar a nova versão do modelo neural, execute:")
    print(f"   python scripts/treinar_lstm.py --version {target_version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixa amostras validadas para retreino")
    parser.add_argument("--api", default="https://sinaliza-api-cn07.onrender.com", help="URL do servidor Node.js")
    parser.add_argument("--token", default=None, help="Token Bearer de autenticação")
    parser.add_argument("--version", default="v2", help="Versão de destino (ex: v2)")
    parser.add_argument("--file", default=None, help="Arquivo JSON exportado pelo dashboard")

    args = parser.parse_args()
    sincronizar_dataset(api_url=args.api, token=args.token, target_version=args.version, json_file=args.file)
