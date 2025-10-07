# receptor.py

import requests
import os
import sys
import json
from transformers import pipeline
from requests.adapters import HTTPAdapter, Retry

# --- Configuration ---
# API endpoints and local file paths
STATIC_ROOT = "static"
UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"
ALPHA_FOLD_API_URL = "https://alphafold.ebi.ac.uk/api/prediction"
OUTPUT_DIR = os.path.join(STATIC_ROOT, sys.argv[1] + "_pdb_files")
OUTPUT_JS = os.path.join(OUTPUT_DIR, "candidate_data.js")
# --- Setup for Robust Network Requests ---
# Use a session with a retry strategy
retries = Retry(total=5, backoff_factor=0.25, status_forcelist=[500, 502, 503, 504])
session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=retries))
session.proxies = { "http": None, "https": None }


# --- Helper Functions ---

def clean_sequence(seq: str) -> str:
    """
    remove other 
    """
    valid_aas = set("ACDEFGHIKLMNPQRSTVWY")
    return "".join([aa for aa in seq.upper() if aa in valid_aas])

def print_step(message):
    """Prints a formatted step message to the console."""
    print("\n" + "="*60)
    print(f"STEP: {message}")
    print("="*60)

def setup_environment():
    """Creates the necessary output directory."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")
    else:
        print(f"Database already contained: {OUTPUT_DIR}")
        sys.exit(1)

def get_ai_assisted_uniprot_query(protein_name):
    """
    **Conceptual Placeholder for an AI-powered query builder.**
    """
    print("--> Using AI assistant to generate an optimized UniProt query...")
    query_map = {
        "dispersin b": '(gene:dspB) AND (organism_id:714)', # Taxon ID for Aggregatibacter actinomycetemcomitans
         "dnas1_bovin": '(gene:DNASE1) AND (organism_id:9913)'
    }
    optimized_query = query_map.get(protein_name.lower(), f'(protein_name:"{protein_name}")')
    return f'{optimized_query} AND (reviewed:true)'

def find_enzyme_for_ligand(ligand_description):
    """
    **Conceptual Placeholder for an AI-powered enzyme lookup.**
    """
    print(f"--> Using AI assistant to find an enzyme for ligand: '{ligand_description}'")
    ligand_to_enzyme_map = {
        "pga": "Dispersin B",
        "beta(1,6)-linked n-acetylglucosamine": "Dispersin B",
        "poly-n-acetylglucosamine": "Dispersin B",
        "dna":"DNAS1_BOVIN",
        "protein":"Proteinase K"
    }
    enzyme_name = ligand_to_enzyme_map.get(ligand_description.lower())
    if enzyme_name:
        print(f"SUCCESS: Found template enzyme: {enzyme_name}")
        return enzyme_name
    else:
        print(f"WARNING: Could not find a known enzyme for '{ligand_description}'.")
        return None

# --- Part 1: Data Retrieval ---

def get_uniprot_data_by_name(protein_name):
    """
    Queries UniProt using an AI-assisted query and falls back to simpler searches if needed.
    """
    ai_query = get_ai_assisted_uniprot_query(protein_name)
    print(f"Querying UniProt with AI-generated query: '{ai_query}'...")

    params = {"query": ai_query, "fields": "accession,id,protein_name,sequence", "format": "json", "size": 1}
    try:
        response = session.get(UNIPROT_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            entry = data["results"][0]
            uniprot_id = entry['primaryAccession']
            sequence = entry['sequence']['value']
            protein_display_name = entry.get('proteinName', {}).get('fullName', {}).get('value', protein_name)
            print(f"SUCCESS: Found UniProt entry: {uniprot_id} ({protein_display_name})")
            return uniprot_id, sequence
    except requests.exceptions.RequestException as e:
        print(f"ERROR: AI-assisted UniProt API request failed: {e}")

    print("\n--> AI-assisted query failed. Falling back to a broader search...")
    fallback_query = f'(protein_name:"{protein_name}")'
    params['query'] = fallback_query

    try:
        response = session.get(UNIPROT_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            entry = data["results"][0]
            uniprot_id = entry['primaryAccession']
            sequence = entry['sequence']['value']
            protein_display_name = entry.get('proteinName', {}).get('fullName', {}).get('value', protein_name)
            print(f"SUCCESS (on fallback): Found UniProt entry: {uniprot_id} ({protein_display_name})")
            return uniprot_id, sequence
        else:
            print(f"ERROR: No UniProt entry found for '{protein_name}' even with fallback.")
            return None, None

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallback UniProt API request failed: {e}")
        return None, None


def download_alphafold_pdb(uniprot_id):
    """
    Downloads the PDB file from the AlphaFold database using the UniProt ID.
    """
    if not uniprot_id: return None
    print(f"Downloading AlphaFold 3D structure for UniProt ID: {uniprot_id}...")
    url = f"{ALPHA_FOLD_API_URL}/{uniprot_id}"
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        pdb_url = data[0]['pdbUrl']
        print(f"Found PDB URL: {pdb_url}")

        pdb_response = session.get(pdb_url, timeout=60)
        pdb_response.raise_for_status()

        pdb_file_path = os.path.join(OUTPUT_DIR, f"{uniprot_id}_alphafold.pdb")
        with open(pdb_file_path, 'w') as f:
            f.write(pdb_response.text)
        print(f"SUCCESS: AlphaFold PDB file saved to: {pdb_file_path}")
        return pdb_file_path, pdb_response.text

    except Exception as e:
        print(f"ERROR: AlphaFold download failed: {e}")
        return None, None

# --- Part 2: Novel Sequence Generation (with ZymCTRL) ---

def compare_sequences_to_find_mutations(original_seq, novel_seq):
    """Helper function to identify mutations between two sequences."""
    mutations = []
    comparison_length = min(len(original_seq), len(novel_seq))
    for i in range(comparison_length):
        orig_aa = original_seq[i]
        novel_aa = novel_seq[i]
        if orig_aa != novel_aa and novel_aa.isalpha() and orig_aa.isalpha():
            mutations.append(f"{orig_aa}{i+1}{novel_aa}")
    return mutations

def generate_novel_sequences_with_zymctrl(original_sequence, maxLength, num_to_generate=3):
    """Uses the AI4PD/ZymCTRL model to generate multiple novel enzyme sequences."""
    print(f"Generating {num_to_generate} novel sequence candidates with ZymCTRL...")
    candidate_sequences = []
    try:
        generator = pipeline('text-generation', model='AI4PD/ZymCTRL')
        if maxLength == None:
            max_len = len(original_sequence)
        else:
            max_len = maxLength
        generated_outputs = generator("<|endoftext|>", max_length=max_len, num_return_sequences=num_to_generate)

        for output in generated_outputs:
            raw_novel_sequence = output['generated_text']
            novel_sequence = raw_novel_sequence.replace("<|endoftext|>", "").replace(" ", "").strip()[:max_len]
            candidate_sequences.append(novel_sequence)

        print(f"SUCCESS: Generated {len(candidate_sequences)} candidates.")
        return candidate_sequences

    except Exception as e:
        print(f"ERROR: An error occurred during ZymCTRL sequence generation: {e}")
        return []

# --- Part 3: Save Files for Manual Analysis ---

def save_files_for_manual_analysis(original_sequence, candidate_sequences, uniprot_id):
    """
    Saves candidate sequences and their corresponding mutation lists to files
    for manual analysis with tools like DynaMut2 and AutoDock.
    """
    if not candidate_sequences:
        print("No candidate sequences to save.")
        return

    print("Saving candidate sequences and mutation lists to files...")

    # ✅ store fasta
    original_fasta_filename = os.path.join(OUTPUT_DIR, sys.argv[1]+".fasta")
    with open(original_fasta_filename, 'w') as f:
        f.write(f">original|{uniprot_id}\n")
        f.write(f"{original_sequence}\n")
    print(f"✅ Saved original sequence to: {original_fasta_filename}")

    for i, candidate_seq in enumerate(candidate_sequences):
        candidate_num = i + 1
        print(f"\n--- Processing Candidate {candidate_num} ---")

        # Save the candidate sequence to a FASTA file
        fasta_filename = os.path.join(OUTPUT_DIR, f"candidate_{candidate_num}_{sys.argv[1]}.fasta")
        fasta_header = f">candidate_{candidate_num}|from_{uniprot_id}"
        clean_seq = clean_sequence(candidate_seq)
        with open(fasta_filename, 'w') as f:
            f.write(f"{fasta_header}\n")
            f.write(f"{clean_seq}\n")
        print(f"  - Saved sequence to: {fasta_filename}")

        # Generate and save the mutation list
        mutations = compare_sequences_to_find_mutations(original_sequence, candidate_seq)
        if mutations:
            mutation_filename = os.path.join(OUTPUT_DIR, f"mutations_candidate_{candidate_num}_{uniprot_id}.txt")
            with open(mutation_filename, 'w') as f:
                f.write("\n".join(mutations))
            print(f"  - Saved {len(mutations)} mutations to: {mutation_filename}")
        else:
            print("  - No mutations found for this candidate.")
# --- Part 4: turn to js file ---
def turn_candidates_to_js_files():
  candidate_dict = {}
  print("\n\nStrat turn files into .js file")
  for filename in sorted(os.listdir(OUTPUT_DIR)):
      if filename.endswith(".fasta"):
          filepath = os.path.join(OUTPUT_DIR, filename)
          with open(filepath, "r", encoding="utf-8") as f:
              content = f.read()
          if filename.startswith("candidate_"):
            key = "_".join(filename.split("_")[:2])  # 取前兩段 "candidate_1"
          else:
            key = filename.replace(".fasta", "")
          # take candidate_x as key
          candidate_dict[key] = {
              "filename": filename,
              "content": content
          }

  # write in js
  with open(OUTPUT_JS, "w", encoding="utf-8") as f:
      f.write("window.candidates = ")
      json.dump(candidate_dict, f, indent=2)
      f.write(";")

  print(f"✅ GENERETED {OUTPUT_JS}")
# --- Main Orchestrator ---

def main():
    """Main function to run the complete workflow."""
    setup_environment()


    ligand_description = sys.argv[1]
    number_of_generate = int(sys.argv[2])
    max_length = None
    #sys.argv[3]
    if sys.argv[3] == '':
        pass
    else:
        max_length = int(sys.argv[3])

    print_step("Part 1.1: Finding a Template Enzyme for the Ligand")
    protein_name = find_enzyme_for_ligand(ligand_description)
    if not protein_name:
        print("\nWorkflow stopped: Could not find a suitable enzyme template.")
        return

    uniprot_id, original_sequence = get_uniprot_data_by_name(protein_name)
    if not uniprot_id or not original_sequence:
        print("\nWorkflow stopped: Could not retrieve UniProt data for the template enzyme.")
        return

    print_step("Part 1.2: Downloading Template PDB Structure from AlphaFold")
    # This PDB will be used as the structural reference for manual analysis
    download_alphafold_pdb(uniprot_id)

    print_step("Part 2: Generating Novel Sequence Candidates (ZymCTRL)")
    candidate_sequences = generate_novel_sequences_with_zymctrl(original_sequence, max_length, num_to_generate= number_of_generate) # Generate more candidates

    print_step("Part 3: Saving Files for Manual Analysis")
    save_files_for_manual_analysis(original_sequence, candidate_sequences, uniprot_id)

    print("\n\nWorkflow finished.")
    print(f"All generated files can be found in the '{OUTPUT_DIR}' directory.")

    turn_candidates_to_js_files()

if __name__ == "__main__":
    main()
