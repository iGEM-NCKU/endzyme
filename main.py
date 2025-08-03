from flask import Flask, jsonify, request
from flask_cors import CORS
import os 
import subprocess
from blast import align_sequences
app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app) # cross domain

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
    try:
        subprocess.run(["python", "receptor.py", ligand], check=True)
        return jsonify({"message": f"✅ receptor.py successful executed，ligand = {ligand}"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"❌ receptor.py failed：{e}"}), 500

@app.route('/api/confirm', methods=['POST'])
def confirm_candidate():
    data = request.get_json()
    candidate = data.get('candidate', '')

    if not candidate:
        return jsonify({"error": "No Candidate select"}), 400

    print(f"[LOG] {candidate} selected")
    
    # 👉 可加入記錄、進一步處理、寫入檔案等
    return jsonify({"message": f"✅ received：{candidate}"})

@app.route('/api/dockLigand', methods=['POST'])
def receive_dockLigand():
    data = request.get_json()
    dockLigand = data.get('dockLigand', '')
    try:
        subprocess.run(["python", "getLigand.py", dockLigand], check=True)
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
        subprocess.run(["bash", "script.sh", ligand, receptor], cwd="./dockingFolder", check=True)
        return jsonify({"message": "✅ Docking successful executed"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"❌ Docking failed：{e}"}), 500

@app.route("/api/alignment", methods=["POST"])
def api_alingment():
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
