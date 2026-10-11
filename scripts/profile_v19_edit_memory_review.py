"""Read-only packet coverage/token audit. Never dispatch a model."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.skill_evolution.review_contract_v19 import MemoryReviewInput
from src.skill_evolution.edit_memory_review_v19 import build_edit_packets,packet_profile
from src.skill_evolution.evolution_replay_v19 import _save

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    request=MemoryReviewInput(args.input.read_text())
    packets=build_edit_packets(request)
    args.output.mkdir(parents=True,exist_ok=False)
    _save(args.output/'profile.json',packet_profile(request,packets))
    for i,p in enumerate(packets):_save(args.output/f'edit-{i:03d}-input.json',p.payload)
    print(args.output/'profile.json')
if __name__=='__main__':main()
