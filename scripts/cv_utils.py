import numpy as np

def extrair_keypoints(results, coletar_rosto=True):
    """
    Extrai os landmarks do MediaPipe Holistic e os retorna em um único vetor achatado.
    """
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    mao_esq = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    mao_dir = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    
    if coletar_rosto:
        face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
        return np.concatenate([pose, face, mao_esq, mao_dir])
    else:
        return np.concatenate([pose, mao_esq, mao_dir])

def normalizar_vetor_keypoints(res, tem_rosto=True):
    """
    Aplica a normalização relativa geométrica a um vetor de features do MediaPipe Holistic.
    Invariante a translação (centralização no punho/ombros) e escala (tamanho da mão/ombros).
    """
    # Separa os subvetores dependendo se o rosto está incluso
    if tem_rosto:
        pose_raw = res[:132]
        face_raw = res[132:1536]
        lh_raw = res[1536:1599]
        rh_raw = res[1599:]
    else:
        pose_raw = res[:132]
        lh_raw = res[132:195]
        rh_raw = res[195:]
        
    # 1. Normalizar Pose (Corpo)
    pose_pts = pose_raw.reshape(33, 4).copy()
    if not np.all(pose_pts == 0):
        # Centro dos ombros: ombro esquerdo (index 11) e direito (index 12)
        sh_left = pose_pts[11, :3]
        sh_right = pose_pts[12, :3]
        sh_mid = (sh_left + sh_right) / 2.0
        
        # Translação: define o ponto médio dos ombros como a origem (0, 0, 0)
        pose_pts[:, :3] = pose_pts[:, :3] - sh_mid
        
        # Escala: divide pela distância entre os ombros para normalizar escala
        sh_dist = np.linalg.norm(sh_left - sh_right)
        if sh_dist > 1e-5:
            pose_pts[:, :3] = pose_pts[:, :3] / sh_dist
    pose_norm = pose_pts.flatten()
    
    # 2. Normalizar Mão Esquerda
    lh_pts = lh_raw.reshape(21, 3).copy()
    if not np.all(lh_pts == 0):
        # Translação: define o punho (index 0) como a origem (0, 0, 0)
        wrist = lh_pts[0]
        lh_pts = lh_pts - wrist
        
        # Escala: divide pela distância entre o punho (0) e a articulação central MCP (9)
        hand_size = np.linalg.norm(lh_pts[9])
        if hand_size > 1e-5:
            lh_pts = lh_pts / hand_size
    lh_norm = lh_pts.flatten()
    
    # 3. Normalizar Mão Direita
    rh_pts = rh_raw.reshape(21, 3).copy()
    if not np.all(rh_pts == 0):
        # Translação: define o punho (index 0) como a origem (0, 0, 0)
        wrist = rh_pts[0]
        rh_pts = rh_pts - wrist
        
        # Escala: divide pela distância entre o punho (0) e a articulação central MCP (9)
        hand_size = np.linalg.norm(rh_pts[9])
        if hand_size > 1e-5:
            rh_pts = rh_pts / hand_size
    rh_norm = rh_pts.flatten()
    
    # Re-concatena os vetores
    if tem_rosto:
        face_pts = face_raw.reshape(468, 3).copy()
        if not np.all(face_pts == 0):
            # Translação: define a ponta do nariz (index 4) como a origem (0, 0, 0)
            nose = face_pts[4]
            face_pts = face_pts - nose
            
            # Escala: divide pela largura do rosto (distância entre têmpora esquerda 234 e têmpora direita 454)
            face_width = np.linalg.norm(face_pts[234] - face_pts[454])
            if face_width > 1e-5:
                face_pts = face_pts / face_width
        face_norm = face_pts.flatten()
        return np.concatenate([pose_norm, face_norm, lh_norm, rh_norm])
    else:
        return np.concatenate([pose_norm, lh_norm, rh_norm])
