from Bio.Align import PairwiseAligner
from Bio import SeqIO
def align_sequences(seq1, seq2, mode="global"):
    aligner = PairwiseAligner(match_score = 1.0,open_gap_score = -1.0, mismatch_score = -1.0)
    
    aligner.mode = mode  # 'global' or'local'

    alignments = aligner.align(seq1, seq2)
    top_alignment = alignments[0]

    return {
        "score": top_alignment.score,
        "alignment": str(top_alignment),
        "mode": mode
    }
