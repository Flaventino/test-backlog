import json, subprocess, os

def run_gh(args):
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    return result.stdout.strip()

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
