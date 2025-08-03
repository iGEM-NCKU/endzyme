import requests
import os
import re
import time
import sys
from urllib.parse import quote

# --- Configuration ---
# API endpoints and local file paths
UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"
ALPHA_FOLD_API_URL = "https://alphafold.ebi.ac.uk/api/prediction"
PUBCHEM_API_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
KEGG_REST_URL = "https://rest.kegg.jp"
OUTPUT_DIR = "enzyme_ligand_structures"

# Use a session with a retry strategy for robust network requests
session = requests.Session()
retries = requests.adapters.Retry(total=5, backoff_factor=0.25, status_forcelist=[500, 502, 503, 504])
session.mount("https://", requests.adapters.HTTPAdapter(max_retries=retries))


# --- Helper Functions ---
def write_in_js():
    pass
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


# --- Dynamic Enzyme Discovery via KEGG ---

def find_enzyme_via_kegg(ligand_name):
    """
    Finds an enzyme for a ligand by querying the KEGG database.
    """
    print(f"--> Querying KEGG database for ligand: '{ligand_name}'")
    try:
        # Step 1: Find KEGG Compound ID from ligand name (with URL encoding)
        encoded_ligand_name = quote(ligand_name)
        find_url = f"{KEGG_REST_URL}/find/compound/{encoded_ligand_name}"

        response = session.get(find_url, timeout=20)
        response.raise_for_status()
        if not response.text:
            print(f"WARNING: Ligand '{ligand_name}' not found in KEGG.")
            return None
        ligand_id = response.text.split('\n')[0].split('\t')[0]
        print(f"--> Found KEGG Ligand ID: {ligand_id}")
        time.sleep(0.1)

        # Step 2: Find a reaction involving this ligand
        link_url = f"{KEGG_REST_URL}/link/reaction/{ligand_id}"
        response = session.get(link_url, timeout=20)
        response.raise_for_status()
        if not response.text:
            print(f"WARNING: No KEGG reactions found for {ligand_id}.")
            return None
        reaction_id = response.text.split('\n')[0].split('\t')[1]
        print(f"--> Found associated reaction: {reaction_id}")
        time.sleep(0.1)

        # Step 3: Find an enzyme (EC number) for this reaction
        link_url = f"{KEGG_REST_URL}/link/enzyme/{reaction_id}"
        response = session.get(link_url, timeout=20)
        response.raise_for_status()
        if not response.text:
            print(f"WARNING: No enzymes found for reaction {reaction_id}.")
            return None
        ec_number = response.text.split('\n')[0].split('\t')[1]
        print(f"--> Found Enzyme Commission (EC) Number: {ec_number}")
        time.sleep(0.1)

        # Step 4: Get the common enzyme name from the EC number
        get_url = f"{KEGG_REST_URL}/get/{ec_number}"
        response = session.get(get_url, timeout=20)
        response.raise_for_status()

        enzyme_name = None
        for line in response.text.split('\n'):
            if line.startswith("NAME"):
                enzyme_name = line.replace("NAME", "").strip().split(';')[0]
                break

        if enzyme_name:
            print(f"SUCCESS: Found template enzyme name: {enzyme_name}")
            return enzyme_name
        else:
            print(f"WARNING: Could not extract a common name for EC {ec_number}.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"ERROR: An error occurred while querying the KEGG database: {e}")
        return None
    except (IndexError, KeyError):
        print(f"ERROR: Could not parse the KEGG database response for '{ligand_name}'.")
        return None


# --- Data Retrieval and Saving ---

def get_uniprot_data_by_name(protein_name):
    """
    Queries UniProt to get the canonical accession ID for a protein.
    """
    print(f"--> Querying UniProt for '{protein_name}'...")
    # The requests library automatically URL-encodes params, so no extra step needed here.
    params = {
        "query": f'(protein_name:"{protein_name}") AND (reviewed:true)',
        "fields": "accession,protein_name", "format": "json", "size": 1
    }
    try:
        response = session.get(UNIPROT_SEARCH_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            uniprot_id = data["results"][0]['primaryAccession']
            print(f"SUCCESS (reviewed): Found UniProt ID: {uniprot_id}")
            return uniprot_id
    except requests.exceptions.RequestException as e:
        print(f"WARNING: UniProt API request failed: {e}")

    print("--> No reviewed entry found. Falling back to broader search...")
    params['query'] = f'(protein_name:"{protein_name}")'
    try:
        response = session.get(UNIPROT_SEARCH_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            uniprot_id = data["results"][0]['primaryAccession']
            print(f"SUCCESS (fallback): Found UniProt ID: {uniprot_id}")
            return uniprot_id
        else:
            print(f"ERROR: No UniProt entry found for '{protein_name}'.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallback UniProt API request failed: {e}")
        return None

def get_and_save_enzyme_structure(protein_name, output_dir):
    """
    Retrieves protein data from UniProt, downloads its structure from
    AlphaFold, and saves it as a PDB file.
    """
    uniprot_id = get_uniprot_data_by_name(protein_name)
    if not uniprot_id:
        return

    print(f"--> Downloading AlphaFold structure for UniProt ID: {uniprot_id}...")
    af_url = f"{ALPHA_FOLD_API_URL}/{uniprot_id}"
    try:
        response = session.get(af_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data or 'pdbUrl' not in data[0]:
            print(f"ERROR: No AlphaFold prediction found for {uniprot_id}.")
            return

        pdb_url = data[0]['pdbUrl']
        pdb_response = session.get(pdb_url, timeout=60)
        pdb_response.raise_for_status()

        safe_protein_name = re.sub(r'[^a-zA-Z0-9_-]', '_', protein_name)
        pdb_filename = f"{uniprot_id}_{safe_protein_name}.pdb"
        pdb_path = os.path.join(output_dir, pdb_filename)
        with open(pdb_path, 'w', encoding='utf-8') as f:
            f.write(pdb_response.text)
        print(f"SUCCESS: Saved enzyme structure to: {pdb_path}")

    except Exception as e:
        print(f"ERROR: AlphaFold download failed for {uniprot_id}: {e}")

def get_and_save_ligand_structure(ligand_name, output_dir):
    """
    Finds a ligand on PubChem, downloads its 3D structure, and saves it
    as an SDF file.
    """
    print(f"--> Searching PubChem for '{ligand_name}'...")
    try:
        encoded_ligand_name = quote(ligand_name)
        search_url = f"{PUBCHEM_API_URL}/compound/name/{encoded_ligand_name}/cids/JSON"

        response = session.get(search_url, timeout=20)
        response.raise_for_status()
        cid = response.json()['IdentifierList']['CID'][0]
        print(f"SUCCESS: Found PubChem CID: {cid}")

        download_url = f"{PUBCHEM_API_URL}/compound/cid/{cid}/SDF?record_type=3d"
        sdf_response = session.get(download_url, timeout=30)
        sdf_response.raise_for_status()

        safe_ligand_name = re.sub(r'[^a-zA-Z0-9_-]', '_', ligand_name)
        file_path = os.path.join(output_dir, f"{safe_ligand_name}_ligand.sdf")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sdf_response.text)
        print(f"SUCCESS: Saved ligand structure to: {file_path}")
        print("--> NOTE: Ligand structure is in SDF format (viewable in PyMOL, Chimera, etc.).")

    except requests.exceptions.RequestException:
        print(f"ERROR: Could not retrieve data from PubChem for '{ligand_name}'.")
    except (KeyError, IndexError):
        print(f"ERROR: No PubChem entry found for '{ligand_name}'. Please try a more specific name.")


# --- Main Orchestrator ---

def main():
    """Main function to run the complete workflow."""
    setup_environment()
    ligand_input = sys.argv[1]

    # # Part 1: Find and Download Enzyme Structure
    # print_step("Part 1: Find and Download Enzyme Structure")
    # protein_name = find_enzyme_via_kegg(ligand_input)
    # if protein_name:
    #     get_and_save_enzyme_structure(protein_name, OUTPUT_DIR)
    # else:
    #     print("\nSkipping enzyme download as no enzyme could be found.")

    # Part 2: Find and Download Ligand Structure
    print_step("Part 2: Find and Download Ligand Structure")
    get_and_save_ligand_structure(ligand_input, OUTPUT_DIR)

    print("\n\n" + "*"*60)
    print("WORKFLOW FINISHED")
    print(f"All downloaded files are in the '{OUTPUT_DIR}' directory.")
    print("*"*60)


if __name__ == "__main__":
    main()