from flask import Flask, jsonify, request
from flask_cors import CORS
import os 
import sys
import logging
import subprocess
import csv
import uuid
from datetime import datetime
from pathlib import Path
from blast import align_sequences

CONDA_PREFIX = os.environ.get("CONDA_PREFIX", "/home/richie/miniconda3")


PYTHON_FOR_RECEPTOR_PY = f"{CONDA_PREFIX}/bin/python"
APP_ROOT = Path(__file__).resolve().parent
PYTHON   = sys.executable
RECEPTOR = APP_ROOT / "receptor.py"
GET_LIGAND = APP_ROOT / "getLigand.py"

#conda env for colab
COLAB_ENV = "colab_local"                           
RUNS_ROOT = Path("/af2_runs")
RUNS_ROOT.mkdir(parents=True, exist_ok=True)

# using https://github.com/YoshitakaMo/localcolabfold?tab=readme-ov-file
AF2_PATH = APP_ROOT / "localcolabfold/colabfold-conda/bin/colabfold_batch"

app = Flask(__name__, static_url_path='/static', static_folder='static')

# for setting server
# CORS(app,resources={
#     r"/api/*":{"origins" : ["http://localhost:4000", "http://54.237.111.117"]},
#     r"/static/*": {"origins": ["http://localhost:4000", "http://54.237.111.117"]
#     }})

logging.basicConfig(
    filename='/home/richie/Endzyme/endzyme.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@app.route('/api/message')
def message():
    return jsonify({"message": "Hello from server!"})

PDB_DIR = 'pdb_files'
@app.route('/api/pdb/<filename>')
def get_pdb(filename):
    filepath = os.path.join(PDB_DIR, filename + '.pdb')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            pdb_data = f.read()
        return jsonify({"pdb": pdb_data})
    else:
        return jsonify({"error": "PDB file not found"}), 404
    
@app.route('/api/ligand', methods=['POST'])
def receive_ligand():
    data = request.get_json()
    ligand = data.get('ligand', '')
    number = data.get('number_of_generate', '')
    max_length = data.get('max_length', '')
    try:
        subprocess.run([PYTHON_FOR_RECEPTOR_PY, str(RECEPTOR), ligand, number, max_length],
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            check=True)
        return jsonify({
            "message": f"receptor.py executed, ligand={ligand}"
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"❌ receptor.py failed：{e}"}), 500

@app.route('/api/confirm', methods=['POST'])
def confirm_candidate():
    data = request.get_json()
    candidate = data.get('candidate', '')

    if not candidate:
        return jsonify({"error": "No Candidate select"}), 400

    print(f"[LOG] {candidate} selected")
    
    jsonify({"message": f"✅ received：{candidate}"})

    # start generate .pdbfile
    ligand = data.get('ligand', '') #ex. PGA
    user_fasta = APP_ROOT / "static" /f"{ligand}" +"_pdb_files" / f"{candidate}" + "_" +f"{ligand}" + ".fasta"
    af2_dir = APP_ROOT / "static" /f"{ligand}" +"_pdb_files" / "af2"
    af2_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([AF2_PATH,"--msa-mode single_sequence" ,user_fasta,af2_dir, "--num-recycle", 1, '--num-models', 2])
    
@app.route('/api/dockLigand', methods=['POST'])
def receive_dockLigand():
    data = request.get_json()
    dockLigand = data.get('dockLigand', '')
    try:
        subprocess.run([PYTHON, str(GET_LIGAND), dockLigand],
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            check=True)
        return jsonify({"message": f"✅ successful executed，ligand = {dockLigand}"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"❌ receptor.py failed：{e}"}), 500
    
@app.route('/api/startDocking', methods=['POST'])
def start_docking():
    data = request.get_json()
    ligand = data.get("ligand", "")
    receptor = data.get("receptor", "")

    if not ligand or not receptor:
        return jsonify({"error": "❌ There is no ligand or receptor"}), 400
    
    try:
        result = subprocess.run(["bash", "script.sh", ligand, receptor], cwd="./dockingFolder", text=True,capture_output=True,check=True)
        output = result.stdout
        error_output = result.stderr
        return jsonify ({"message": "✅ Docking successful executed",
                        "stdout": output,
            "stderr": error_output  })
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"❌ Docking failed：{e}"}), 500

@app.route("/api/alignment", methods=["POST","OPTIONS"])
def api_alingment():
    if request.method == "OPTIONS":
        return "", 204
    
    data = request.json
    seq1 = data.get("seq1")
    seq2 = data.get("seq2")
    mode = data.get("mode","global")
    
    if not seq1 or not seq2:
        return jsonify({"error":"need seq1 and seq2"}), 400
    try:
         result = align_sequences(seq1, seq2, mode)
         return jsonify({
            "message": "✅ Alignment finished",
            "score": result["score"],
            "alignment": result["alignment"],
            "mode": result["mode"]
        })
    except Exception as e:
        return jsonify({"error": f"❌ Alignment failed: {e}"}), 500


def _build_colab_cmd(csv_path: Path, job_dir: Path,
                     use_templates: str, custom_tpl_dir: str|None,
                     amber: bool, models: int|None, recycles: int|None):
    cmd = [
        "colabfold_batch","--msa-mode", "single_sequence",       
        str(csv_path), str(job_dir)
    ]
    if use_templates == "pdb100":
        cmd.append("--templates")
    elif use_templates == "custom" and custom_tpl_dir:
        cmd += ["--templates", "--custom-template-path", str(Path(custom_tpl_dir).resolve())]

    if amber:
        cmd.append("--amber")

    if isinstance(models, int):
        cmd += ["--num-models", str(models)]   
    if isinstance(recycles, int):
        cmd += ["--num-recycle", str(recycles)]  

    return cmd

def launch(cmd, job_dir: Path):
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / f"run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    lf = open(log_path, "w")
    lf.write("Command: " + " ".join(cmd) + "\n\n"); lf.flush()

    proc = subprocess.Popen(
        cmd, cwd=str(job_dir),
        stdout=lf, stderr=lf,
        start_new_session=True,      # zombie
    )
    (job_dir / "pid").write_text(f"{proc.pid}\n")
    return {"ok": True, "log": log_path.name, "pid": proc.pid}

def api_fold():
    """
    JSON body:
    {
      "sequence": "PIAQI...ASK",          
      "jobname": "test123",               
      "templates": "none|pdb100|custom",  x
      "custom_template_dir": "/path/..",  
      "amber": true|false,              
      "models": 5,                       
      "recycles": 3,                      
      "force_cpu": false                  
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    seq = (data.get("sequence") or "").strip().replace("\n", "").replace(" ", "")
    if not seq:
        return jsonify({"ok": False, "error": "Empty sequence"}), 400

    jobname = data.get("jobname") or f"job_{uuid.uuid4().hex[:8]}"
    use_templates = data.get("templates", "none")
    custom_tpl_dir = data.get("custom_template_dir")
    amber = bool(data.get("amber", False))
    models = data.get("models")
    recycles = data.get("recycles")
    force_cpu = bool(data.get("force_cpu", False))

    job_dir = RUNS_ROOT / jobname
    job_dir.mkdir(parents=True, exist_ok=True)
    # cp fasta file to job_dir

    csv_path = job_dir / f"{jobname}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "sequence"]); w.writerow([jobname, seq])

    try:
        cmd = _build_colab_cmd(csv_path, job_dir, use_templates, custom_tpl_dir, amber, models, recycles)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    try:
        info = launch(cmd, job_dir, force_cpu=force_cpu)
    except Exception as e:
        logging.exception("Failed to start colabfold")
        return jsonify({"ok": False, "error": f"Failed to start ColabFold: {e}"}), 500

    return jsonify({
        "ok": True,
        "jobname": jobname,
        "log": info["log"],
        "pid": info["pid"],
        "cmd": cmd
    })


if __name__ == '__main__':
    app.run(port=5001)
