import os, json
from pathlib import Path
from scripts.exp.researcher.idea_pool import Idea, Idea_Pool

script_dir = Path(__file__).parent
idea_path = script_dir / "scripts/exp/researcher/output_dir/idea"
idea_files = [file for file in os.listdir(idea_path) if file.endswith('.json')]

max_num = 50
count = 0
pool = Idea_Pool()
for file in idea_files: 
    with open(f"{idea_path}/{file}", "r") as f:
        data = json.load(f)
    for idea in data:
        count += 1
        pool.add_new_idea(idea)
        if count > max_num:
            break
    if count > max_num:
        break

output_path = script_dir / "scripts/exp/researcher/output_dir/idea_pool/test.json"
pool.save_to_cache(str(output_path))