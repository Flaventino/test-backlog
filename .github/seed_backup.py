# ///   I M P O R T S   ///
import json
import subprocess
import os
import sys
import time
from typing import Any
from datetime import datetime, timedelta


# ///   G L O B A L   C O N S T A N T S   ///
LOCK_FILE = 'deployed.lock'
BASE_TIME = datetime.now()
ID_MAP: dict[str, str] = {}
REPO: str | None = os.environ.get('GITHUB_REPOSITORY')


# ///   F U N C T I O N S   ///

# ### VALIDATION ENGINE ###
def validate_backlog(data: dict[str, Any]) -> bool:
    """Checks JSON structure and dependencies before execution.

    Args:
        data: The raw dictionary loaded from the JSON file.

    Returns:
        True if the structure and dependencies are valid, False otherwise.
    """
    # --- Setup ---
    deps: list[str] = []
    all_ids: set[str] = set()

    # --- First-level controls ---
    if 'project_name' not in data:
        print("FATAL: Missing 'project_name\' at root level.")
        return False

    if 'milestones' not in data:
        print("FATAL: Missing 'milestones' at root level.")
        return False

    # --- Second-level controls ---
    for ms in data.get('milestones'):
        
        for key in ["id", "title", "duration_days"]:
            if key not in ms:
                print(f"FATAL: Milestone missing key: {key}")
                return False

        for epic in ms.get("epics", []):
            for key in ["id", "title"]:
                if key not in epic:
                    print(f"FATAL: Epic {ms['id']} missing key: {key}")
                    return False

            for task in epic.get("tasks", []):
                if "id" not in task or "title" not in task:
                    print(f"FATAL: Task in {epic['id']} missing ID/Title")
                    return False

                all_ids.add(task["id"])
                if task.get("depends_on"):
                    deps.append(task["depends_on"])

    for d in deps:
        if d not in all_ids:
            print(f"FATAL: Dependency '{d}' points to a ghost task.")
            return False

    return True


# ### GITHUB INTERFACE ###
def run_gh(args: list[str]) -> str:
    """Executes a GitHub CLI command and captures its output.

    Args:
        args: A list of command-line arguments for the 'gh' executable.

    Returns:
        The stripped standard output or an empty string on error.
    """
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"DEBUG ERROR: {result.stderr}")

    return result.stdout.strip() if result.returncode == 0 else ""


# ///   MAIN DEPLOYMENT LOGIC   ///


def main() -> None:
    """Orchestrates the creation of GitHub Milestones and Issues.

    This function coordinates the safety checks, data loading, validation,
    and the sequential creation of project resources on GitHub.
    """
    # --- 1. Safety Check ---
    if os.path.exists(LOCK_FILE):
        print("⚠️ PROJECT ALREADY DEPLOYED. Aborting.")
        sys.exit(0)

    # --- 2. Load and Validate Data ---
    try:
        with open(".github/backlog.json", "r", encoding="utf-8") as file:
            plan: dict[str, Any] = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as err:
        print(f"❌ JSON LOAD ERROR: {err}")
        sys.exit(1)

    if not validate_backlog(plan):
        print("❌ VALIDATION FAILED. No resources created.")
        sys.exit(1)

    # --- 3. Deployment Loop ---
    for ms in plan["milestones"]:
        # Date calculation
        delta = ms['start_delay'] + ms['duration_days']
        end_date = BASE_TIME + timedelta(days=delta)
        iso_due = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"\n🏗️ Creating Milestone: {ms['title']}")
        run_gh([
            "api", f"repos/{REPO}/milestones",
            "-f", f"title={ms['title']}",
            "-f", f"due_on={iso_due}"
        ])

        time.sleep(1) # Safety delay for GitHub API consistency
        m_no = run_gh([
            "api", f"repos/{REPO}/milestones",
            "--jq", f'.[] | select(.title=="{ms["title"]}") | .number'
        ])
        ID_MAP[ms["id"]] = m_no

        for epic in ms["epics"]:
            # Create Epic Issue
            e_url = run_gh([
                "issue", "create", "--title", epic['title'],
                "--body", f"Phase: {ms['title']}",
                "--milestone", m_no, "--label", "epic"
            ])
            e_no = e_url.split("/")[-1]
            ID_MAP[epic["id"]] = e_no

            task_list_md = ""
            for t in epic["tasks"]:
                estimate = t.get("estimate", "None Yet")
                dep_id = t.get("depends_on")
                desc = t.get("description", f"Part of {epic['title']}")

                # Dependency linkage
                block = f"\n\n⛔ **Blocked by:** #{ID_MAP[dep_id]}" \
                    if dep_id and dep_id in ID_MAP else ""

                t_url = run_gh([
                    "issue", "create", "--title", t['title'],
                    "--body", f"{desc}\nEstimate: {estimate}{block}",
                    "--milestone", m_no
                ])

                t_no = t_url.split("/")[-1]
                ID_MAP[t["id"]] = t_no
                task_list_md += f"- [ ] #{t_no} {t['title']}\n"

            # Update Epic with the final checklist
            run_gh([
                "issue", "edit", e_no,
                "--body", f"### 📋 Epic Backlog\n{task_list_md}"
            ])

    # --- 4. Finalize Deployment ---
    with open(LOCK_FILE, "w", encoding="utf-8") as lock:
        lock.write("DEPLOYED")
    print("\n🎯 Dynamic deployment successful.")


if __name__ == "__main__":
    main()






















# # ///   I M P O R T S   ///
# import json, subprocess, os, sys, time
# from typing import Sequence
# from datetime import datetime, timedelta


# # ///   G L O B A L S   ///
# LOCK_FILE = 'deployed.lock'
# PLAN_FILE = 'backlog.json'
# REPO_NAME = os.environ.get('GITHUB_REPOSITORY')
# ISO_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
# START_DATE = datetime.now()


# # ///   F U N C T I O N S   ///    
# def run_gh(args: list[str]) -> str:
#     """Executes a GitHub CLI command and returns the output.

#     Thin wrapper around ``subprocess.run`` for ``gh``. It captures
#     stdout/stderr, prints stderr on non‑zero exit, and returns the
#     stripped stdout. No exception is raised by this helper.

#     Args:
#         args: Command parts after ``gh``.
#               Example: ``["issue", "create", "--title", "X"]``.

#     Returns:
#         The command stdout with surrounding whitespace stripped.
#         May be empty on success for some subcommands.

#     Notes:
#         On failure (non‑zero exit code), stderr is printed to help
#         debugging, and the function still returns stdout (possibly
#         empty).
#     """
#     result = subprocess.run(['gh'] + args, capture_output=True, text=True)
#     if result.returncode != 0:
#         print(f'DEBUG ERROR: {result.stderr}')
#     return (result.stdout or '').strip()

# # def issue_create(
# #     title: str,
# #     body: str,
# #     milestone: int | str,
# #     labels: str | Sequence[str] | None = None,
# # ) -> str:
# #     """Create a GitHub issue and return its URL.

# #     Args:
# #         title: Issue title.
# #         body: Issue body in Markdown.
# #         milestone: Milestone number (int or str).
# #         labels: One label (str) or a sequence of labels.

# #     Returns:
# #         The created issue URL as returned by ``gh issue create``.
# #     """
# #     # --- Setup ---
# #     labels = [labels] if isinstance(labels, str) else labels
# #     arguments = [
# #         "issue", "create",
# #         "--title", title,
# #         "--body", body,
# #         "--milestone", str(milestone),
# #     ]

# #     # --- Process Labels ---
# #     for lab in (labels if labels else []):
# #         arguments.extend(["--label", str(lab)])

# #     return run_gh(arguments)

# # def issue_edit(number: int | str, body: str) -> str:
# #     """Replace an issue body.

# #     Args:
# #         number: Issue number or string identifier.
# #         body: New Markdown content for the issue body.

# #     Returns:
# #         The stdout from ``gh issue edit`` (usually empty on success).
# #     """
# #     return run_gh(["issue", "edit", str(number), "--body", body])


# # ///   M A I N   S C R I P T   ///
# # ### SAFETY LOCK ###
# lock_file = 'deployed.lock'
# if os.path.exists(lock_file):
#     print('⚠️  PROJECT ALREADY DEPLOYED: Aborting to prevent duplicates.')
#     sys.exit(0)

# # ### LOAD DATA ###
# try:
#     file_path = f'.github/{PLAN_FILE}'
#     with open(file_path, encoding='utf-8') as f:
#         plan = json.load(f)
# except FileNotFoundError:
#     print(f'❌ ERROR: {PLAN_FILE} not found in .github/ directory.')
#     sys.exit(1)

# # ### PLAN DEPLOYMENT ###
# print(f'🏗️  Deploying: {plan.get("project_name", "Unnamed Project")}')
# task_ids = {}
# block_msg = lambda id: f"\n\n⛔ **Blocked by:** #{task_ids.get(id)}"

# for ms in plan.get('milestones', []):
#     # --- Milestone setup ---
#     title = ms.get('title')
#     target = f'repos/{repo}/milestones'
#     offset = int(ms.get('start_delay', 0))
#     duration = int(ms.get('duration_days', 0))
#     target_api = f'repos/{REPO_NAME}/milestones'

#     # --- Due date calculation ---
#     due_date = (START_DATE + timedelta(offset + duration)).strftime(ISO_FORMAT)
    
#     # --- Creating Milestone ---
#     print(f'\n📅 Creating Milestone: {title} | Due: {due_date}')
#     run_gh([
#         'api', target,
#         '-f', f'title={title}',
#         '-f', f'due_on={due_date}',
#     ])

#     # --- Get milestone ID ---
#     time.sleep(1) # API Throttling protection
#     jq_filter = f'.[] | select(.title=="{title}") | .number'
#     milestone_id = run_gh([
#         'api', target_api,
#         '--jq', jq_filter,
#         ])

#     # --- Epics processing ---
#     for epic in ms.get('epics', []):
#         # Epic setup
#         epic_body = f'Phase: {title}'
#         epic_title = epic.get('title')

#         # Creating Epic
#         epic_url = run_gh([
#             'issue', 'create',
#             '--title', epic_title,
#             '--body', epic_body,
#             '--milestone', milestone_id,
#             '--label', 'epic',
#         ])

#         # Get epic ID
#         epic_id = epic_url.rsplit('/', 1)[-1]

#         # Tasks Processing
#         tasks = []
#         for task in epic.get('tasks', []):
#             # Task setup
#             estim = task.get('estimate', 'N/A')
#             dep_id = task.get('depends_on')
#             task_title = task['title']

#             # Dependency Mapping Logic
#             block_msg = block_msg(dep_id) if dep_id in task_ids else ""
# ###############################################################################
# ###############################################################################
    
#     # print(f"\n📅 Milestone: {ms.get('title')}")
    
#     # # Create Milestone
    
#     # due_date = ms.get('due_on')
#     # run_gh(["api", f"repos/{REPO}/milestones", "-f", f"title={ms['title']}", "-f", f"due_on={due_date}"])
    
#     # time.sleep(1) # API protection
#     # m_no = run_gh(["api", f"repos/{REPO}/milestones", "--jq", f'.[] | select(.title=="{ms["title"]}") | .number'])

#     # for epic in ms["epics"]:
#     #     # Create EPIC
#     #     e_url = run_gh(["issue", "create", "--title", epic['title'], "--body", "Initializing tasks...", "--milestone", m_no, "--label", "epic"])
#     #     e_no = e_url.split("/")[-1]
        
#     #     task_list_md = ""
#     #     created_tasks = {}

#     #     for t in epic["tasks"]:
#     #         # Setup metadata for the body
#     #         dep_text = f"\n\n⚠️ **Depends on:** #{created_tasks.get(t['depends_on'])}" if "depends_on" in t else ""
#     #         est_text = f"\n⏱️ **Estimate:** {t.get('estimate', 'N/A')}"
            
#     #         # Create Task
#     #         t_url = run_gh(["issue", "create", "--title", t['title'], "--body", f"Linked to Epic #{e_no}{dep_text}{est_text}", "--milestone", m_no])
#     #         t_no = t_url.split("/")[-1]
            
#     #         # Record ID for dependencies
#     #         task_key = t.get('id', t['title'])
#     #         created_tasks[task_key] = t_no
#     #         task_list_md += f"- [ ] #{t_no} {t['title']}\n"
        
#     #     # Update Epic with the checklist
#     #     full_body = f"{epic.get('body', '')}\n\n### 📋 Task Checklist\n{task_list_md}"
#     #     run_gh(["issue", "edit", e_no, "--body", full_body])





# # 1. Charger les données
# with open(".github/backlog.json") as f:
#     data = json.load(f)

# # 2. Créer Milestone et Epic
# run_gh(["api", f"repos/{os.environ['GITHUB_REPOSITORY']}/milestones", "-f", f"title={data['milestone']['title']}"])
# epic_url = run_gh(["issue", "create", "--title", data['epic']['title'], "--body", data['epic']['body']])
# epic_id = epic_url.split("/")[-1]

# # 3. Créer les tâches et construire la check-list
# task_links = ""
# created_ids = {}

# for t in data["tasks"]:
# # BACKUP
# #     # Remplacer le tag ID_T1 par le vrai numéro généré
# #     body = t["body"]
# #     for tid, real_no in created_ids.items():
# #         body = body.replace(f"#ID_{tid}", f"#{real_no}")
    
# #     issue_url = run_gh(["issue", "create", "--title", t["title"], "--body", body, "--label", t["labels"], "--milestone", data['milestone']['title']])
# #     real_id = issue_url.split("/")[-1]
# #     created_ids[t["id"]] = real_id
# #     task_links += f"- [ ] #{real_id}\n"

#     print(f"--- Création de la tâche : {t['title']} ---")
    
#     # Remplacer les tags de dépendance
#     body = t["body"]
#     for tid, real_no in created_ids.items():
#         body = body.replace(f"#ID_{tid}", f"#{real_no}")
    
#     # Création de l'issue et capture précise du numéro
#     # On ajoute --json number pour être sûr d'avoir le chiffre
#     cmd = ["issue", "create", "--title", t["title"], "--body", body, "--label", t["labels"], "--milestone", data['milestone']['title'], "--json", "number", "--jq", ".number"]
#     real_id = run_gh(cmd)
    
#     if real_id:
#         print(f"Succès : Issue #{real_id} créée.")
#         created_ids[t["id"]] = real_id
#         task_links += f"- [ ] #{real_id} {t['title']}\n"
#     else:
#         print(f"ERREUR : Impossible de récupérer l'ID pour {t['title']}")


# # # 4. Mettre à jour l'Epic avec la check-list visuelle
# # BACKUP
# # run_gh(["issue", "edit", epic_id, "--body", f"{data['epic']['body']}\n\n### Tasks\n{task_links}"])

# print(f"Mise à jour de l'Epic #{epic_id}...")
# run_gh(["issue", "edit", epic_id, "--body", f"{data['epic']['body']}\n\n### Tasks\n{task_links}"])
# print(f"✅ Terminé ! Epic #{epic_id} créé avec ses tâches.")
