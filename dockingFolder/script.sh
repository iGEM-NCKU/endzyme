#!/usr/bin/env bash

ligand_dir="../enzyme_ligand_structures"
receptor_dir="../static"

ligand=$1
receptor=$2

echo "Ligand name: $ligand"
echo "Receptor name: $receptor"

ligand_sdf="$ligand_dir/${ligand}_ligand.sdf"
receptor_cif="$receptor_dir/${receptor}_pdb_files/${receptor}.cif"

cp "$ligand_sdf" ./
cp "$receptor_cif" ./

pymol -cQ turn_file_into_pdb.py -- "${ligand}_ligand.sdf" "${receptor}.cif"

# === PDBQT File===
receptor_pdb="receptor.pdb"
ligand_pdb="ligand.pdb"

receptor_pdbqt="receptor.pdbqt"
ligand_pdbqt="ligand.pdbqt"

# === PDBQT prepartion ===

echo "Preparing input files..."

# turn protein.pdb → protein.pdbqt
if [ ! -f "$receptor_pdbqt" ]; then
    if [ -f "$receptor_pdb" ]; then
        echo "[INFO] Generating $receptor_pdbqt from $receptor_pdb"
        "/c/Program Files (x86)/MGLTools-1.5.7/python.exe" \
        "/c/Program Files (x86)/MGLTools-1.5.7/Lib/site-packages/AutoDockTools/Utilities24/prepare_receptor4.py" \
        -r "$receptor_pdb" -o "$receptor_pdbqt"
    else
        echo "[ERROR] Receptor PDB file not found: $receptor_pdb"
        exit 1
    fi
else
    echo "[INFO] Receptor $receptor_pdbqt already exists, skipping conversion."
fi

# turn ligand.pdb/mol2 → ligand.pdbqt
if [ ! -f "$ligand_pdbqt" ]; then
    if [ -f "$ligand_pdb" ]; then
        echo "[INFO] Generating $ligand_pdbqt from $ligand_pdb"
        "/c/Program Files (x86)/MGLTools-1.5.7/python.exe" \
        "/c/Program Files (x86)/MGLTools-1.5.7/Lib/site-packages/AutoDockTools/Utilities24/prepare_ligand4.py" \
        -l "$ligand_pdb" -o "$ligand_pdbqt"
    else
        echo "[ERROR] Ligand PDB file not found: $ligand_pdb"
        exit 1
    fi
else
    echo "[INFO] Receptor $ligand_pdbqt already exists, skipping conversion."
fi
# === GRIDBOX PREPARE ===

pymol -cq get_gridbox.py -- $ligand_pdbqt $receptor_pdbqt


# check Windows-vina
if ! command -v Windows-vina &> /dev/null; then
  echo "Error: vina not found in PATH"
  exit 1
fi


# # check source
# if [ "$1" = "-l" ]; then
#     filter_mode="-l"
# elif [ "$1" = "-s" ]; then
#     filter_mode="-s"
# else
#     echo "Usage: ./docking.sh [-l | -s]"
#     echo "  -l  Select results with low RMSD and good affinity"
#     echo "  -s  Select results with scattered RMSD and good affinity"
#     exit 1
# fi

#init
maxattempt=2
if [ ! -d "results" ]
then
	mkdir results
fi

if [ ! -f "results/results_table.csv" ]; then
	echo "Average dist from rmsd value,Maximum dist from rmsd value,Lowest affinity value,Average best mode rmsd value,Result seed,Result number" > results_table.csv
fi
config=$(ls | grep 'conf.txt')
result_count=$(ls -A results/ | wc -l)
for ((i = $result_count+1; i<=maxattempt; i++))
do
	echo "$i started..."
	Windows-vina --config $config > results/result_$i.txt
	linenum=$(wc -l results/result_$i.txt | awk -F' ' '{print $1}')
	if [ "$linenum" -gt 35 ]
	then
		dist_from_rmsd_average=$(sed '0,/^mode/d' results/result_$i.txt | sed '1,2d;12d' | awk -F' ' '{print $3}' | awk '{sum+=$1} END {print sum/8}')
		dist_from_rmsd_maximum=$(sed '0,/^mode/d' results/result_$i.txt | sed '1,2d;12d' | awk -F' ' '{print $3}' | sort -n | tail -1)
		best_affinity=$(sed '0,/^mode/d' results/result_$i.txt | sed '1,2d;12d' | awk -F' ' '{print $2}' | sort -n | head -1)
		best_mode_rmsd_average=$(sed '0,/^mode/d' results/result_$i.txt | sed '1,2d;12d' | awk -F' ' '{print $4}' | awk '{sum+=$1} END {print sum/8}')
		docking_seed=$(grep "seed" results/result_$i.txt | awk '{print $4}')
		echo "$dist_from_rmsd_average,$dist_from_rmsd_maximum,$best_affinity,$best_mode_rmsd_average,$docking_seed,$i" >> results_table.csv
	fi
	sort -go results_table.csv results_table.csv
	echo "$i done.
Average dist from rmsd value: $dist_from_rmsd_average
Maximum dist from rmsd value: $dist_from_rmsd_maximum
Lowest affinity value: $best_affinity
"
done
echo "Process finished"

#
#echo "Analyzing results..."
#python filter_results.py

# cp csv
cp results_table.csv ../static/${receptor}_pdb_files/results_table.csv
echo "CSV copied to static directory."

#
# delete all file
rm *.pdb *.pdbqt *.csv *.txt *.cif *.sdf 2>/dev/null \
&& echo "all those files have been deleted............." \
|| echo "you have already removed the files"

echo "Process finished."

# >"C:\Program Files (x86)\MGLTools-1.5.7\python.exe" "C:\Program Files (x86)\MGLTools-1.5.7\Lib\site-packages\AutoDockTools\Utilities24\prepare_receptor4.py" -r fold_dsp_b_ori_model_0.cif dspb_ori.pdbqt