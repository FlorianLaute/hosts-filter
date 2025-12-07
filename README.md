# Hosts Filter

Une application Python moderne (TUI) pour gérer votre fichier `/etc/hosts` en y fusionnant des listes de blocage (malware, spam, publicités, etc.) tout en préservant vos entrées systèmes.

## Fonctionnalités

*   **Récupération** : Télécharge les dernières listes depuis des sources fiables (URLHaus, StevenBlack, etc.).
*   **Protection** : Préserve automatiquement vos entrées existantes dans `/etc/hosts`.
*   **Sélection** : Choisissez précisément quelles listes activer.
*   **Interface** : Utilise une interface terminal moderne (Textual) avec support de la souris.

## Installation

1.  **Prérequis** : Python 3.
2.  **Créer un environnement virtuel** :
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Installer les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

## Utilisation

L'application doit modifier `/etc/hosts`, elle nécessite donc les droits **root**.

1.  **Lancer l'application** :
    ```bash
    sudo venv/bin/python main.py
    ```

2.  **Dans l'interface** :
    *   Cliquez sur **"Fetch & Analyze"** (ou touche `f`) pour télécharger les listes.
    *   Cochez les cases des listes que vous voulez utiliser.
    *   Cliquez sur **"Preview Merge"** (ou touche `p`) pour voir le nombre d'entrées.
    *   Cliquez sur **"Apply to /etc/hosts"** (ou touche `a`) pour écrire les changements.

> **Note** : Une sauvegarde de votre ancien fichier hosts est créée sous `/etc/hosts.bak`.

## Raccourcis Clavier

*   `q` : Quitter
*   `f` : Fetch (Récupérer les listes)
*   `p` : Preview (Prévisualiser)
*   `a` : Apply (Appliquer)
