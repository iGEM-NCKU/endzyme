# turn_file_into_pdb.py
import sys
from pymol import cmd

ligand_input_file = sys.argv[1]
receptor_input_file = sys.argv[2]

ligand_output_file = "ligand.pdb"
receptor_output_file = "receptor.pdb"

cmd.load(ligand_input_file, "receptor") 
cmd.load(receptor_input_file, "ligand")        

cmd.save(ligand_output_file, "receptor")
cmd.save(receptor_output_file, "ligand")

cmd.quit()