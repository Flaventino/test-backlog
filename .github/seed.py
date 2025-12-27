import json, subprocess, os, sys, time

def run_gh(args):
    """Executes a GitHub CLI command and returns the output."""
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"DEBUG ERROR: {result.stderr}")
    return result.stdout.strip()

# --- 1. SAFETY LOCK ---
lock_file = "deployed.lock"
if os.path.exists(lock_file):
    print("⚠️  PROJECT ALREADY DEPLOYED: Aborting to prevent duplicates.")
    sys.exit(0)
else:
    REPO = os.environ.get('GITHUB_REPOSITORY')

# --- 2. LOAD DATA ---
plan_file = 'backlog.json'
try:
    with open(f'.github/{plan_file}') as f:
        plan = json.load(f)
except FileNotFoundError:
    print(f'❌ ERROR: {plan_file} not found in .github/ directory.')
    sys.exit(1)

print(f"🏗️  Deploying: {plan.get('project_name', 'Unnamed Project')}")

# --- 3. PROCESSING ---
for ms in plan["milestones"]:
    print(f"\n📅 Milestone: {ms.get('title')}")
    
    # Create Milestone
    
    due_date = ms.get('due_on')
    run_gh(["api", f"repos/{REPO}/milestones", "-f", f"title={ms['title']}", "-f", f"due_on={due_date}"])
    
    time.sleep(1) # API protection
    m_no = run_gh(["api", f"repos/{REPO}/milestones", "--jq", f'.[] | select(.title=="{ms["title"]}") | .number'])

    for epic in ms["epics"]:
        # Create EPIC
        e_url = run_gh(["issue", "create", "--title", epic['title'], "--body", "Initializing tasks...", "--milestone", m_no, "--label", "epic"])
        e_no = e_url.split("/")[-1]
        
        task_list_md = ""
        created_tasks = {}

        for t in epic["tasks"]:
            # Setup metadata for the body
            dep_text = f"\n\n⚠️ **Depends on:** #{created_tasks.get(t['depends_on'])}" if "depends_on" in t else ""
            est_text = f"\n⏱️ **Estimate:** {t.get('estimate', 'N/A')}"
            
            # Create Task
            t_url = run_gh(["issue", "create", "--title", t['title'], "--body", f"Linked to Epic #{e_no}{dep_text}{est_text}", "--milestone", m_no])
            t_no = t_url.split("/")[-1]
            
            # Record ID for dependencies
            task_key = t.get('id', t['title'])
            created_tasks[task_key] = t_no
            task_list_md += f"- [ ] #{t_no} {t['title']}\n"
        
        # Update Epic with the checklist
        full_body = f"{epic.get('body', '')}\n\n### 📋 Task Checklist\n{task_list_md}"
        run_gh(["issue", "edit", e_no, "--body", full_body])





# 1. Charger les données
with open(".github/backlog.json") as f:
    data = json.load(f)

# 2. Créer Milestone et Epic
run_gh(["api", f"repos/{os.environ['GITHUB_REPOSITORY']}/milestones", "-f", f"title={data['milestone']['title']}"])
epic_url = run_gh(["issue", "create", "--title", data['epic']['title'], "--body", data['epic']['body']])
epic_id = epic_url.split("/")[-1]

# 3. Créer les tâches et construire la check-list
task_links = ""
created_ids = {}

for t in data["tasks"]:
# BACKUP
#     # Remplacer le tag ID_T1 par le vrai numéro généré
#     body = t["body"]
#     for tid, real_no in created_ids.items():
#         body = body.replace(f"#ID_{tid}", f"#{real_no}")
    
#     issue_url = run_gh(["issue", "create", "--title", t["title"], "--body", body, "--label", t["labels"], "--milestone", data['milestone']['title']])
#     real_id = issue_url.split("/")[-1]
#     created_ids[t["id"]] = real_id
#     task_links += f"- [ ] #{real_id}\n"

    print(f"--- Création de la tâche : {t['title']} ---")
    
    # Remplacer les tags de dépendance
    body = t["body"]
    for tid, real_no in created_ids.items():
        body = body.replace(f"#ID_{tid}", f"#{real_no}")
    
    # Création de l'issue et capture précise du numéro
    # On ajoute --json number pour être sûr d'avoir le chiffre
    cmd = ["issue", "create", "--title", t["title"], "--body", body, "--label", t["labels"], "--milestone", data['milestone']['title'], "--json", "number", "--jq", ".number"]
    real_id = run_gh(cmd)
    
    if real_id:
        print(f"Succès : Issue #{real_id} créée.")
        created_ids[t["id"]] = real_id
        task_links += f"- [ ] #{real_id} {t['title']}\n"
    else:
        print(f"ERREUR : Impossible de récupérer l'ID pour {t['title']}")


# # 4. Mettre à jour l'Epic avec la check-list visuelle
# BACKUP
# run_gh(["issue", "edit", epic_id, "--body", f"{data['epic']['body']}\n\n### Tasks\n{task_links}"])

print(f"Mise à jour de l'Epic #{epic_id}...")
run_gh(["issue", "edit", epic_id, "--body", f"{data['epic']['body']}\n\n### Tasks\n{task_links}"])
print(f"✅ Terminé ! Epic #{epic_id} créé avec ses tâches.")
