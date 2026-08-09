"""
Transformer model load + inference 
"""


import os 
import io 
import numpy as np 
import chess 
import chess.pgn 
import onnxruntime as ort 
from pathlib import Path 

#Config
MODEL_PATH = os.getenv("MODEL_PATH", "models/transformer.onnx")
MAX_SEQ_LEN = 128 
BOARD_CHANNELS = 17 
N_TIME_FEATS = 3 

PIECE_CHANNEL = {
    (chess.PAWN,   chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK,   chess.WHITE): 3,
    (chess.QUEEN,  chess.WHITE): 4,
    (chess.KING,   chess.WHITE): 5,
    (chess.PAWN,   chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK,   chess.BLACK): 9,
    (chess.QUEEN,  chess.BLACK): 10,
    (chess.KING,   chess.BLACK): 11,
}


_session: ort.InferenceSession | None = None

def load_model() -> None: 
    """Load ONNX model into global session """
    global _session 
    
    if not Path(MODEL_PATH).exists(): 
        print(f"WARNING: No ONNX model found at {MODEL_PATH} — Elo prediction unavailable")
        return
    
    _session = ort.InferenceSession(
        MODEL_PATH,
        providers=["CPUExecutionProvider"], 
    )
    
    print(f"Loaded ONNX model from {MODEL_PATH}")

def fen_to_tensor(fen: str) -> np.ndarray: 
    """Encode FEN string into (17,8,8) tensor """
    
    tensor = np.zeros((BOARD_CHANNELS, 8, 8) , dtype = np.float32)
    try: 
        board = chess.Board(fen) 
        for sq, piece in board.piece_map().items(): 
            ch   = PIECE_CHANNEL[(piece.piece_type, piece.color)]
            rank = chess.square_rank(sq)
            file = chess.square_file(sq)
            tensor[ch, rank, file] = 1.0
        
        if board.turn == chess.WHITE:
            tensor[12] = 1.0
        if board.has_kingside_castling_rights(chess.WHITE):
            tensor[13] = 1.0
        if board.has_queenside_castling_rights(chess.WHITE):
            tensor[14] = 1.0
        if board.has_kingside_castling_rights(chess.BLACK):
            tensor[15] = 1.0
        if board.has_queenside_castling_rights(chess.BLACK):
            tensor[16] = 1.0
    except Exception: 
        pass 
    
    return tensor 

def predict_elo(moves:list[dict]) -> tuple[float, float]: 
    """
    Run Elo prediction inference on list of moves 
    
    """
    
    if _session is None: 
        raise RuntimeError("Model not loaded. Retry again later")
    
    seq_len = min(len(moves), MAX_SEQ_LEN)
    moves = moves[:seq_len]
    
    board_tensors = np.stack([
        fen_to_tensor(m["fen_before"]) for m in moves
    ])[np.newaxis].astype(np.float32)
    
    time_features = np.zeros((1, seq_len, N_TIME_FEATS), dtype=np.float32)

    attention_mask = np.ones((1, seq_len), dtype=np.float32)
    
    outputs = _session.run(
        output_names = ["elo_pred"],
        input_feed   = {
            "board_tensors":  board_tensors,
            "time_features":  time_features,
            "attention_mask": attention_mask,
        }
    )
    
    elo_pred  = outputs[0][0]  
    white_elo = float(np.clip(elo_pred[0], 500, 3000))
    black_elo = float(np.clip(elo_pred[1], 500, 3000))
 
    return white_elo, black_elo
 





    
    
