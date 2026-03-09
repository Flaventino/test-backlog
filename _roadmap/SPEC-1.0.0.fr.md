# SPEC-1.0.0 — Protocole de Formalisation et d'Instanciation de Projets Informatiques

Ce document définit le protocole **SPEC-1.0.0** pour formaliser un projet sous forme d'un fichier JSON ("plan"), puis l'instancier via un outil d'automatisation.

> **Référence normative :** la version française fait foi.  
> Une traduction anglaise est fournie dans `SPEC-1.0.0.en.md`.

---

## Portée et relation à l'implémentation

### Objet de ce protocole

Ce document définit le protocole **SPEC-1.0.0**, dont l'objet est de **formaliser un projet informatique sous forme d'un fichier JSON structuré** (appelé "plan").

### Écosystème

Ce protocole fait partie d'un kit cohérent comprenant :
- **SPEC-1.0.0** (ce document) : définition du format JSON décrivant Milestones, Epics, Tasks et leurs dépendances
- **roadmap.yml** (l'Orchestrateur) : Fichier YAML d'une GitHub Action manuelle orchestrant la matérialisation de la roadmap
- **materialize_plan.py** (l'Ouvrier qualifié et spécialisé) : Script de matérialisation vers GitHub Issues
- **README.md** : Documentation utilisateur

### Finalité

Le plan JSON résultant de l'instanciation du présent protocole est destiné à être **déployé** (matérialisé) sur une plateforme de gestion de projet (ex: GitHub Issues) via un **outil d'automatisation** (GitHub Action + script).

### Ce que définit ce protocole

- ✅ La **structure du fichier JSON** (champs, types, hiérarchie)
- ✅ Les **règles de validité** (contraintes d'intégrité, cohérence sémantique)
- ✅ Les **conventions de nommage** et bonnes pratiques recommandées

### Ce que ce protocole NE définit PAS

Les détails d'implémentation du processus de matérialisation (orchestration workflow, algorithmes, gestion erreurs API, configuration).

**Pour ces aspects, consulter le README.**

### Notes de lecture

Les mentions de "validation", "script", ou "outil" dans ce document décrivent le comportement attendu d'un outil conforme (ex: "les IDs doivent être uniques") tel que celui proposé dans le kit évoqué ci-dessus. Elles ne prescrivent pas l'implémentation interne.

---

## 1. L'Individu "MILESTONE" (Le Gardien du Temps)

Le Milestone est l'unité de synchronisation globale. Il ne produit rien par lui-même, il délimite. C'est le tuteur ultime : rien n'existe sur la carte sans lui être rattaché (Règle de Tutelle).

### Configurations possibles

- **Le Jalon Actif** : Contient des Epics et/ou des Tâches. Il représente une phase de production.

- **Le Jalon de Contrôle (Gate)** : Vide de contenu. Il représente une date de décision, une fin de contrat ou un événement externe.
  
  **Contrainte stricte :** Un milestone de configuration "Gate" ne DOIT contenir aucune Epic ni aucune Task (ni directement, ni indirectement via des Epics qui lui seraient rattachées). La présence de contenu viole la définition même d'un Gate et constitue une erreur de données.
  
  **Exemples d'usage :**
  - Revue client (jalon décisionnel sans production)
  - Date contractuelle fixe (livraison, fin de contrat)
  - Point de synchronisation externe (attente validation tiers)

### Inventaire des caractéristiques

- **ID (Unique)** : Référence interne pour le système (ADN).
- **Titre** : Nom clair de la phase (ex: "Bêta Publique").
- **Start_Delay (Inertie)** : Entier (jours). Nombre de jours d'attente, depuis T0 (date de début du projet), avant le lancement de ce Jalon. Permet le parallélisme.
- **Duration (Fenêtre)** : Entier (jours). Temps alloué pour réaliser tout le contenu interne.
- **Description** : Note stratégique sur l'objectif de la phase (Note d'intention). *(Optionnel — bonnes pratiques)*
- **Date d'échéance (Calculée)** : `T0 + Start_Delay + Duration`. *(Où T0 est la date de lancement effective, spécifiée au déploiement.)*

---

## 2. L'Individu "EPIC" (Le Gardien du Sens)

L'Epic est un conteneur thématique. Elle sert à organiser la pensée et à regrouper les efforts sans notion de temps propre. C'est un sous-conteneur optionnel à structure plate (ne peut pas contenir d'autres Epics).

### Configurations possibles

- **L'Epic Standard** : Un ensemble de tâches concrètes visant une fonctionnalité.
- **L'Epic "Bac à sable" (Discovery)** : Une enveloppe pour des recherches futures, pouvant être vide ou contenir des tâches exploratoires (Veille/Recherche).

### Inventaire des caractéristiques

- **ID (Unique)** : Référence interne.
- **Titre** : Nom fonctionnel ou de la thématique.
- **Description** : Le "Pourquoi" et le périmètre de cette fonctionnalité. *(Optionnel — bonnes pratiques)*
- **Label** : Tag permettant de filtrer les Epics sur un tableau de bord. *(Optionnel)*
- **Parent_ID (Milestone_ID)** : Identifiant du Milestone auquel elle est rattachée (Lien de tutelle obligatoire).

---

## 3. L'Individu "TÂCHE" (L'Atome d'Action)

La Tâche est la seule unité qui "consomme" de l'effort et qui peut être "bloquée". Elle porte les dépendances techniques.

### Configurations possibles

- **La Tâche Indépendante** : Peut être réalisée n'importe quand durant son Milestone.
- **La Tâche Séquentielle** : Dépend de la complétion d'une ou plusieurs autres tâches.
- **La Tâche Orpheline (Directe)** : Rattachée à un Milestone sans passer par une Epic. Elle possède une tutelle temporelle directe.
- **La Tâche Membre** : Enfermée dans une Epic. Elle possède une double tutelle.

### Inventaire des caractéristiques

- **ID (Unique)** : La clé de voûte pour les dépendances.
- **Titre** : Action concrète (verbe d'action recommandé).
- **Description** : Détails techniques, critères d'acceptation et de succès. *(Optionnel — bonnes pratiques)*
- **Estimate (Effort)** : Grandeur (en heures ou points) représentant la charge de travail.
- **Depends_on** : Liste d'IDs de tâches devant être terminées avant (Séquençage).
- **Parent_Link** : L'ID du Milestone (si orpheline) ou de l'Epic (si membre).
- **Assignee** : *(Optionnel)* Username GitHub de la personne assignée à cette tâche.
  - **Type** : Chaîne de caractères (string)
  - **Format** : Username GitHub valide (alphanumérique et tirets, pas d'espaces, pas de préfixe `@`)
  - **Exemples valides** : `"alice"`, `"john-doe"`, `"dev-team-lead"`
  - **Exemples invalides** : `"@alice"`, `"john doe"`, `""`

### Contraintes de cohérence

Le champ `configuration` d'une tâche DOIT être cohérent avec le type de son `parent_link` :

- Si `configuration = "Orpheline"` → `parent_link` DOIT pointer vers un Milestone
- Si `configuration = "Membre"` → `parent_link` DOIT pointer vers une Epic

**Justification :** Ces configurations décrivent la nature structurelle de la tâche (rattachement direct au temps vs rattachement thématique). Une incohérence révèle une erreur de compréhension du modèle et doit être corrigée.

**Règle de validité :** Un document violant cette contrainte est considéré comme invalide (erreur structurelle).

---

## 4. La Carte des Liens (Le Système Nerveux)

Voici comment ces individus interagissent sur la carte A0, formant le système nerveux du projet :

### Règles de connexion

- **Flux Temporel** : Le projet s'écoule au fil des Milestones (qui peuvent se chevaucher).
- **Lien Milestones → Epics** : Un Milestone peut contenir 0 à n Epics. Une Epic appartient à un seul Milestone.
- **Lien Milestones → Tasks** : Un Milestone peut contenir 0 à n Tasks en direct (Tâches Orphelines). Le rattachement au Milestone est strictement obligatoire.
- **Lien Epics → Tasks** : Une Epic contient 0 à n Tasks. Une Task appartient à une seule Epic (ou aucune si orpheline).
- **Lien Tasks → Tasks (Dépendances)** : Une Task peut dépendre de n Tasks. Condition critique : les tâches "parentes" doivent idéalement appartenir au même Milestone ou à un Milestone antérieur.
- **Lien Temporel** : Le Milestone "englobe" le temps. Toutes les Tasks et Epics contenues dedans héritent de la date d'échéance du Milestone.

### Limites de la validation temporelle

Le protocole SPEC-1.0.0 ne définit pas de dates de début/fin individuelles pour les tâches. Chaque tâche hérite de la plage temporelle de son milestone (`[T0 + start_delay, T0 + start_delay + duration]`).

**Validation D1 (dépendances inter-milestones) :**  
Le script de matérialisation détecte les incohérences temporelles entre milestones (une tâche dépendant d'une autre dont le milestone commence plus tard). Cependant, cette validation ne peut garantir l'ordre d'exécution exact au jour près, notamment :
- Au sein d'un même milestone (toutes les tâches partagent la même plage)
- Entre milestones qui se chevauchent (parallélisme autorisé)

**Responsabilité de l'équipe :**  
L'équipe reste responsable de l'ordonnancement détaillé des tâches selon les dépendances documentées dans les issues GitHub (liens clickables dans les bodies).

**Bonne pratique :**  
Organisez vos milestones de façon séquentielle ou assurez-vous que les milestones des tâches dépendances commencent avant ou simultanément aux milestones des tâches dépendantes.

---

## 5. Spécification Technique de l'Objet d'Instanciation (JSON)

Ce protocole ne se limite pas à une définition conceptuelle ; il impose une structure de données stricte destinée à la matérialisation du projet via un script d'automatisation. Tout interpréteur (humain ou IA) doit produire un fichier au format JSON respectant la version **SPEC-1.0.0** décrite ci-après.

### 5.1 Schéma de structure plate

Afin de garantir une gestion optimale des dépendances croisées (le Système Nerveux), la structure est "plate". Les relations ne sont pas définies par imbrication, mais par l'usage exclusif des identifiants (ID).

#### Modèle d'instanciation (JSON)

> Note : l'exemple ci-dessous est annoté. Le **JSON réel** ne supporte pas les commentaires.

```jsonc
{
  "metadata": {
    "projet_nom": "Nom du Projet",
    "version_protocole": "SPEC-1.0.0",  /* Doit être exactement cette chaîne, sensible à la casse */
    "description": "Note d'intention globale sur le périmètre du projet.",  /* Optionnel */
    "estimate_unit": "days",  /* Obligatoire : "days" | "hours" | "story_points" */
    "velocity": 10  /* Requis uniquement si estimate_unit = "story_points" (points/jour) */
  },
  "milestones": [
    {
      "id": "M-01",  /* Doit être unique globalement ; préfixe recommandé */
      "titre": "Nom du Jalon",
      "configuration": "Actif",  /* Valeurs autorisées : "Actif" ou "Gate" */
      "start_delay": 0,  /* Entier positif ou nul (jours) */
      "duration": 14,  /* Entier positif ou nul (jours) */
      "description": "Objectif stratégique du jalon."  /* Optionnel - bonnes pratiques */
    }
  ],
  "epics": [
    {
      "id": "E-01",  /* Doit être unique globalement ; préfixe recommandé */
      "parent_id": "M-01",  /* Doit référencer un milestone existant */
      "titre": "Nom de l'Epic",
      "configuration": "Standard",  /* Valeurs autorisées : "Standard" ou "Discovery" */
      "label": "Tag_GitHub",  /* Optionnel */
      "description": "Le Pourquoi et le périmètre fonctionnel."  /* Optionnel - bonnes pratiques */
    }
  ],
  "tasks": [
    {
      "id": "T-01",  /* Doit être unique globalement ; préfixe recommandé */
      "parent_link": "E-01",  /* Doit référencer un milestone ou une epic existant(e) */
      "titre": "Action à mener",
      "configuration": "Sequentielle",  /* Valeurs autorisées : "Indépendante", "Sequentielle", "Orpheline", "Membre" */
      "estimate": 4,  /* Nombre positif ou nul (heures/points) */
      "depends_on": ["T-00"],  /* Liste d'IDs de tâches existantes ; vide si indépendante */
      "description": "Critères de succès et détails techniques.",  /* Optionnel - bonnes pratiques */
      "assignee": "Username_GitHub"  /* Optionnel */
    }
  ]
}
```

### 5.2 Contraintes de formalisation

- **Agnosticisme Temporel** : Le JSON ne doit contenir aucune date absolue. Le script d'exécution calculera les échéances à partir d'un point T0 (date du jour par défaut, ou date explicitement fournie au déploiement) en appliquant les variables `start_delay` et `duration`.

- **Timezone T0** : Toutes les dates sont interprétées en UTC (Coordinated Universal Time). Le script compare T0 à la date du jour en UTC pour valider qu'il n'y a pas de rétro-planification. Cette convention garantit un comportement cohérent indépendamment de la localisation géographique des membres de l'équipe.

- **Règle de Tutelle** :
  - Toute Epic doit posséder un `parent_id` valide pointant vers un Milestone existant.
  - Toute Task doit posséder un `parent_link` pointant soit vers une Epic existante (Configuration Membre), soit vers un Milestone existant (Configuration Orpheline).

- **Séquençage** : Le champ `depends_on` est une liste de chaînes de caractères (Array). Si une tâche est "Indépendante", la liste doit être vide `[]`.

- **Codification des IDs** : Il est recommandé d'utiliser des préfixes explicites (`M-`, `E-`, `T-`) suivis d'un index numérique pour faciliter la lecture humaine et le débogage du système nerveux. Le non-respect de cette convention n'est pas une erreur bloquante si l'unicité globale est assurée.

- **Champs optionnels** : Les champs `description` (pour tous les objets), `label` (pour Epic) et `assignee` (pour Task) sont optionnels. Ils peuvent être omis ou valoir `null`.

### 5.3 Sémantique des validations

Les non-conformités doivent être catégorisées comme suit :

- **Erreur bloquante** : violation d'une règle structurelle ou référentielle critique (ex. : champ obligatoire manquant, type incorrect, référence inexistante, ID dupliqué). Une seule erreur bloquante invalide le JSON.
- **Avertissement** : violation d'une recommandation ou incohérence sémantique non critique (ex. : préfixe ID non respecté, absence de description, milestone "Gate" avec contenu, dépendance vers un milestone postérieur).
- **Traitement de l'absence de description** : un avertissement doit être émis pour encourager la documentation ("Consider adding a description to improve project clarity"), mais cela n'invalide pas le JSON.

Le script doit collecter toutes les anomalies et produire un rapport en anglais précisant pour chacune :

- Catégorie (`error`/`warning`)
- Localisation (chemin JSON)
- Description claire
- Suggestion de correction si possible

Il retournera ensuite un statut booléen (`True` si valide, `False` sinon) après affichage du rapport.

---

## 6. Glossaire et définitions

### Résolution du milestone d'une tâche

Chaque tâche appartient à un milestone, qui définit sa fenêtre temporelle de réalisation.

**Règle de résolution :**  
Le milestone auquel appartient une tâche est déterminé par son champ `parent_link` :

- Si `parent_link` pointe vers un **Milestone** → la tâche appartient directement à ce Milestone  
  *Exemple : Task `T-01` avec `parent_link: "M-01"` → appartient au Milestone `M-01`*

- Si `parent_link` pointe vers une **Epic** → la tâche appartient au Milestone de l'Epic  
  *Résolution : `milestone_tâche = epic[parent_link].parent_id`*  
  *Exemple : Task `T-02` avec `parent_link: "E-05"`, et Epic `E-05` avec `parent_id: "M-02"` → appartient au Milestone `M-02`*

**Notation technique** (utilisée dans les règles de validation) :  
On appelle **"milestone effectif"** le résultat de cette résolution. Ce n'est pas un nouveau type de milestone, mais simplement le milestone auquel la tâche appartient *in fine* après résolution du lien parent.