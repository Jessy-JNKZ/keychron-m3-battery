# Keychron M3 Battery Monitor (JJ)

[Français](#français) | [English](#english)

---

## Français

**Keychron M3 Battery Monitor** est un utilitaire léger et élégant pour Windows conçu spécifiquement pour surveiller le niveau de batterie de votre souris **Keychron M3** (via le dongle USB) directement depuis la barre des tâches (systray).

### 🚀 Fonctionnalités
* **Lecture HID Native** : Extraction directe des données matérielles sans nécessiter le logiciel constructeur lourd.
* **Affichage minimaliste et pro** : 4 styles au choix (Cercle épuré, Cercle plein, Batterie horizontale, Batterie verticale) avec codes couleur dynamiques (Vert, Orange, Rouge).
* **Estimation de l'autonomie** : Calcul intelligent du temps restant basé sur l'historique de décharge.
* **Alertes de batterie faible** : Notification native Windows lorsque le niveau descend sous les 15 %.
* **Personnalisation complète** : Modification des seuils de couleurs, de la fréquence d'actualisation et gestion du lancement au démarrage directement depuis le menu contextuel.

### 📦 Installation (Utilisateur Lambda)
1. Téléchargez la dernière version de l'installeur (**`KeychronBatterySetup.exe`**) depuis l'onglet *Releases* du dépôt.
2. Double-cliquez sur le fichier pour lancer l'assistant d'installation.
3. L'application s'installe dans `C:\Program Files (x86)\Keychron` et vous propose de configurer le démarrage automatique ainsi que le lancement immédiat.

### 🛡️ Note concernant les antivirus (Faux Positif)
Lors de l'installation de l'exécutable, **Windows Defender** ou certains antivirus peuvent afficher une alerte de type *Trojan:Win32/Bearfoos.A!ml* et mettre le fichier en quarantaine. 

* **Pourquoi ?** Il s'agit d'un **faux positif** lié à l'algorithme de Machine Learning de l'antivirus. Comme le programme est un script Python converti/emballé et qu'il communique directement avec les flux matériels du système (HID), l'antivirus le signale par précaution car il ne possède pas de signature numérique payante.
* **Que faire ?** Le code source est entièrement ouvert et auditable dans ce dépôt. Si votre antivirus bloque l'application, il vous suffit d'ajouter le dossier d'installation `C:\Program Files (x86)\Keychron` aux **exclusions** de votre antivirus.

---

## English

**Keychron M3 Battery Monitor** is a lightweight and elegant Windows utility designed specifically to monitor the battery level of your **Keychron M3** mouse (via the USB dongle) directly from the system tray.

### 🚀 Features
* **Native HID Communication**: Direct hardware data extraction without heavy vendor software.
* **Clean & Professional UI**: 4 visual styles (Clean circle, Solid circle, Horizontal battery, Vertical battery) with dynamic color coding (Green, Orange, Red).
* **Battery Life Estimation**: Smart time-remaining calculations based on historical usage.
* **Low Battery Alerts**: Native Windows notifications when the battery drops below 15%.
* **Full Customization**: Easily change color thresholds, polling intervals, and startup behavior straight from the tray menu.

### 📦 Installation
1. Download the latest installer (**`KeychronBatterySetup.exe`**) from the *Releases* section.
2. Double-click the file to run the standard installation wizard.
3. The app installs into `C:\Program Files (x86)\Keychron` and lets you choose your startup preferences.

### 🛡️ Antivirus Notice (False Positive)
During installation, **Windows Defender** or other security software may flag the executable as *Trojan:Win32/Bearfoos.A!ml*.

* **Why?** This is a **false positive** triggered by heuristic machine learning algorithms. Because the app interacts directly with low-level USB/HID hardware and lacks an expensive commercial code-signing certificate, antivirus software flags it out of caution.
* **What to do?** The source code is 100% open and reviewable in this repository. If blocked, simply add the installation folder (`C:\Program Files (x86)\Keychron`) to your antivirus **exclusions list**.

---

### 📝 License
Distributed under the MIT License. See `LICENSE` for more information.