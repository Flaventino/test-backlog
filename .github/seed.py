# ###   I M P O R T S   ###
import json, subprocess, os, sys, time
from typing import Sequence
from datetime import datetime, timedelta


# ###   G L O B A L S   ###
LOCK_FILE = "deployed.lock"
PLAN_FILE = "backlog.json"
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
START_DATE = datetime.now()


# ###   F U N C T I O N S   ###
def run_gh(args):
    """Executes a GitHub CLI command and returns the output."""
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"DEBUG ERROR: {result.stderr}")
    return result.stdout.strip()
    
def run_gh(args: list[str]) -> str:
    """Executes a GitHub CLI command and returns the output.

    Thin wrapper around ``subprocess.run`` for ``gh``. It captures
    stdout/stderr, prints stderr on non‑zero exit, and returns the
    stripped stdout. No exception is raised by this helper.

    Args:
        args: Command parts after ``gh``.
              Example: ``["issue", "create", "--title", "X"]``.

    Returns:
        The command stdout with surrounding whitespace stripped.
        May be empty on success for some subcommands.

    Notes:
        On failure (non‑zero exit code), stderr is printed to help
        debugging, and the function still returns stdout (possibly
        empty).
    """
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"DEBUG ERROR: {result.stderr}")
    return (result.stdout or "").strip()
###############################################################################
def issue_create(
    title: str,
    body: str,
    milestone: int | str,
    labels: str | Sequence[str] | None = None,
) -> str:
    """Create a GitHub issue and return its URL.

    Args:
        title: Issue title.
        body: Issue body in Markdown.
        milestone: Milestone number (int or str).
        labels: One label (str) or a sequence of labels.

    Returns:
        The created issue URL as returned by ``gh issue create``.
    """
    args = [
        "issue", "create",
        "--title", title,
        "--body", body,
        "--milestone", str(milestone),
    ]
    if labels:
        if isinstance(labels, (list, tuple, set)):
            for lab in labels:
                args.extend(["--label", str(lab)])
        else:
            args.extend(["--label", str(labels)])
    return run_gh(args)


def issue_edit(number: int | str, body: str) -> str:
    """Replace an issue body.

    Args:
        number: Issue number or string identifier.
        body: New Markdown content for the issue body.

    Returns:
        The stdout from ``gh issue edit`` (usually empty on success).
    """
    return run_gh(["issue", "edit", str(number), "--body", body])


# ###   M A I N   S C R I P T   ###

# --- 1. SAFETY LOCK ---
lock_file = "deployed.lock"
if os.path.exists(lock_file):
    print("⚠️  PROJECT ALREADY DEPLOYED: Aborting to prevent duplicates.")
    sys.exit(0)

# --- 2. CONFIG ---
ids = {}                      # Mapping ID -> GitHub Issue number
day0 = datetime.now()         # Project start date
zulu = "%Y-%m-%dT%H:%M:%SZ"   # Strict ISO 8601 timestamp format
repo = os.environ.get('GITHUB_REPOSITORY')

# --- 3. LOAD DATA ---
plan_file = 'backlog.json'
try:
    with open(f'.github/{plan_file}') as f:
        plan = json.load(f)
except FileNotFoundError:
    print(f'❌ ERROR: {plan_file} not found in .github/ directory.')
    sys.exit(1)

# --- 3. DYNAMIC PROCESSING ---
print(f"🏗️  Deploying: {plan.get('project_name', 'Unnamed Project')}")

for ms in plan["milestones"]:
    # Milestone attribute retrieval
    title, target = ms.get('title'), f"repos/{repo}/milestones"
    offset, duration = ms.get('start_delay'), ms.get('duration_days')

    # Due date calculation
    due_date = (day0 + timedelta(offset + duration)).strftime(zulu)

    # GitHub log update
    print(f"\n📅 Creating Milestone: {title} | Due: {due_date}")

    # Creating Milestone
    run_gh(["api", target, "-f", f"title={title}", "-f", f"due_on={due_date}"])

    # Retrieving the GitHub milestone ID for the last created milestone
    time.sleep(1) # API Throttling protection
    api_query = f'.[] | select(.title=="{title}") | .number'
    milestone_id = run_gh(["api", target, "--jq", api_query])

    # Creating epics & tasks
    for epic in ms.get('epics'):
        # Creating epics
        api_query = 
###############################################################################
    
    # print(f"\n📅 Milestone: {ms.get('title')}")
    
    # # Create Milestone
    
    # due_date = ms.get('due_on')
    # run_gh(["api", f"repos/{REPO}/milestones", "-f", f"title={ms['title']}", "-f", f"due_on={due_date}"])
    
    # time.sleep(1) # API protection
    # m_no = run_gh(["api", f"repos/{REPO}/milestones", "--jq", f'.[] | select(.title=="{ms["title"]}") | .number'])

    # for epic in ms["epics"]:
    #     # Create EPIC
    #     e_url = run_gh(["issue", "create", "--title", epic['title'], "--body", "Initializing tasks...", "--milestone", m_no, "--label", "epic"])
    #     e_no = e_url.split("/")[-1]
        
    #     task_list_md = ""
    #     created_tasks = {}

    #     for t in epic["tasks"]:
    #         # Setup metadata for the body
    #         dep_text = f"\n\n⚠️ **Depends on:** #{created_tasks.get(t['depends_on'])}" if "depends_on" in t else ""
    #         est_text = f"\n⏱️ **Estimate:** {t.get('estimate', 'N/A')}"
            
    #         # Create Task
    #         t_url = run_gh(["issue", "create", "--title", t['title'], "--body", f"Linked to Epic #{e_no}{dep_text}{est_text}", "--milestone", m_no])
    #         t_no = t_url.split("/")[-1]
            
    #         # Record ID for dependencies
    #         task_key = t.get('id', t['title'])
    #         created_tasks[task_key] = t_no
    #         task_list_md += f"- [ ] #{t_no} {t['title']}\n"
        
    #     # Update Epic with the checklist
    #     full_body = f"{epic.get('body', '')}\n\n### 📋 Task Checklist\n{task_list_md}"
    #     run_gh(["issue", "edit", e_no, "--body", full_body])





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
