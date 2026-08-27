# 04-agent-observability-security

## Contexte

Objectif : pratiquer concretement deux competences agentiques restees superficielles
apres 02/03 -- observabilite (traces persistantes + evaluation rejouable) et
securite/permissions Claude Code (jamais observees en action) -- plutot que d'ouvrir
un nouveau grand chapitre. Le pipeline lui-meme est volontairement minimal : ce n'est
pas le sujet du projet, seulement le support pour exercer les deux competences
ci-dessus.

## Le pipeline

Deux sous-agents, definis dans `.claude/agents/` :

- `drafter` : transforme un diff git en resume structure JSON (`type`/`scope`/
  `description`, vocabulaire conventional-commit).
- `reviewer` : relit ce resume face au diff original et donne un verdict qualitatif
  (`approved`/`concerns`) -- jugement authentiquement non-deterministe, assume comme
  tel, a ne jamais confondre avec la validation structurelle ci-dessous.

Le resultat structure de `drafter` doit etre ecrit par l'orchestrateur dans
`fixtures/<cas>/actual_output.json` pour que `tests/run_eval.py` puisse le verifier
(voir plus bas).

Choix de modele : `drafter` en haiku (extraction/classification a faible ambiguite -- meme categorie que link-scanner en 03), `reviewer` en sonnet (jugement qualitatif reel, comparaison semantique diff/resume). A valider concretement via tests/run_eval.py une fois le pipeline execute, pas suppose acquis.

Correction du 27/08/2026, apres verification directe de la doc officielle (pas supposee) : `tools: []` fait tres probablement echouer le lancement du sous-agent ("Agent would be spawned with zero tools", comportement documente depuis Claude Code v2.1.208). Aucune syntaxe confirmee n'existe pour declarer explicitement zero outil -- le champ `tools` est donc omis (herite du pool par defaut) et chaque agent recoit dans son prompt une instruction explicite de ne jamais en utiliser. C'est une restriction de niveau prompt, pas une contrainte mecanique imposee par le systeme -- a garder en tete comme limite reelle du moindre privilege ici, pas un acquis.

## Traces persistantes (hooks)

`.claude/settings.json` declare deux hooks (`PostToolUse`, `SubagentStop`) qui
appellent `scripts/trace_hook.py` a chaque appel d'outil et a chaque fin de
sous-agent. Le script lit le JSON que Claude Code lui passe sur son entree standard
et ajoute une ligne a `traces/<session_id>.jsonl`.

Point important, a verifier plutot que supposer : le schema exact de ce JSON (noms de
champs comme `session_id`, `tool_name`, `hook_event_name`...) est ecrit ici de memoire
de la doc Claude Code, pas verifie en conditions reelles dans ce projet. Le script est
volontairement defensif (`.get()` partout, jamais un acces direct qui casserait sur un
champ absent) et garde tout le payload brut dans chaque ligne de trace (`raw`), pour
qu'aucune information ne soit perdue meme si les noms de champs supposes sont faux.
Premier run reel = l'occasion de corriger ce fichier si besoin, pas juste de le tester.

## Evaluation rejouable

`fixtures/<cas>/` contient un `diff.txt` (entree) et un `expected.json` (regles
verifiables mecaniquement -- jamais une reponse exacte attendue, le texte genere par
`drafter` varie d'un run a l'autre). `tests/run_eval.py` ne fait aucun appel LLM : il
lit `actual_output.json` (produit par un run du pipeline) et verifie les regles en
code pur. Objectif : un score objectif rejouable a chaque changement du prompt de
`drafter`, pas une lecture au juge d'une sortie unique.

Ce que `run_eval.py` verifie reste volontairement structurel (type dans une liste
autorisee, scope coherent, longueur de description) -- juger si le contenu est
semantiquement bon resterait non-deterministe (jugement de type LLM-as-judge), hors
scope ici.

Declenchement volontairement manuel, jamais un hook : contrairement a `trace_hook.py` (observationnel, doit tourner a chaque evenement sans exception), decider qu'un run merite d'etre note est un choix -- de l'orchestrateur (via un appel `Bash` ordinaire, une decision de Tool comme une autre) ou de l'utilisateur en ligne de commande -- jamais un evenement automatique du moteur.

## Workflow git

Meme regle que `03-portfolio-changelog-crew` : jamais de commit ni de push direct sur
`main` apres ce commit de scaffold initial. Toute modification passe par une branche
dediee + pull request, meme petite. Le merge reste une action humaine.

## Prerequis environnement / creation du depot distant

Le depot local existe deja (scaffold initial commite), mais aucun depot GitHub distant
n'a encore ete cree -- le pont Cowork utilise pour ce scaffold n'a ni `gh` ni
credentials de push. Premiere action attendue de Claude Code a l'ouverture de ce
projet, avant tout travail sur le pipeline lui-meme :

- Verifier si `gh` est installe (`gh --version`) ; sinon l'installer soi-meme
  (`winget install --id GitHub.cli --silent --accept-package-agreements
  --accept-source-agreements`), comme en 03-portfolio-changelog-crew.
- S'authentifier soi-meme (`gh auth login --hostname github.com --git-protocol https
  --web`) -- la validation du code affiche reste une etape humaine (device flow),
  impossible a automatiser davantage, mais toute la partie CLI (installation,
  lancement de la commande) est a faire par l'agent, pas a la charge de
  l'utilisateur.
- Creer le depot distant prive et pousser le commit de scaffold existant :
  `gh repo create Carcagno/04-agent-observability-security --private --source=.
  --remote=origin --push`.
- Consigner le lien du depot dans `journal-projets.md` (Project Cowork) une fois fait.

## Partie 2 : securite et permissions (a venir)

Trois experiences deliberees, a mener dans une session Claude Code `--cloud` (isolee
par nature, cf. `roadmap-agentique.md`) sur ce meme depot -- jamais sur la machine
locale :

1. Provoquer un vrai blocage du classifieur (ex. tentative de `git push --force`),
   quel que soit le mode de permission actif.
2. Comparer `dontAsk` et `bypassPermissions` sur une meme action anodine.
3. Tenter une ecriture dans `.claude/` ou `.git/` et observer la protection au moment
   precis de l'action.

Chaque experience doit etre tracee avec le meme mecanisme de hooks que ci-dessus, pour
que le compte-rendu final soit base sur des logs reels et pas sur un recit reconstruit
apres coup.

## Langue

Code, prompts systeme, JSON, messages : anglais des le depart (voir
`.claude/agents/*.md`). Ce fichier et les commentaires pedagogiques restent en
francais -- destines a etre nettoyes avant tout passage en showcase, comme pour les
projets precedents.
