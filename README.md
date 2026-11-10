# Keychron M3 Battery Monitor

[Français](#français) | [English](#english)

---

## Français

**Keychron M3 Battery Monitor** est un utilitaire léger et élégant pour Windows conçu spécifiquement pour surveiller le niveau de batterie de votre souris **Keychron M3** (via le dongle USB) directement depuis la barre des tâches (systray).

> 💡 *Développé par [Jessy JONKISZ](https://x.com/JNKZJessy)*
> 
> ![Icône de l'application](images/Keychron%20App%20ico.png)

### 🚀 Fonctionnalités
* **Lecture HID Native** : Extraction directe des données matérielles sans nécessiter le logiciel constructeur lourd.
* **Affichage minimaliste et pro** : 4 styles d'icônes au choix (Cercle épuré, Cercle plein, Batterie horizontale, Batterie verticale) avec codes couleur dynamiques.
* **Statistiques et Graphique détaillé** : 
  * Fenêtre pop-up dédiée avec suivi visuel de la batterie.
  * Axe temporel sur 24h+ étalonné par tranches fixes de 2 heures.
  * **Tracé intelligent** : Ligne verte continue pour les relevés normaux et ligne pointillée orange pour estimer les périodes hors-ligne (ex. lorsque le PC ou la souris est éteint).
* **Estimation de l'autonomie** : Calcul intelligent du temps restant basé sur l'historique de décharge.
* **Alertes de batterie faible** : Notification native Windows lorsque le niveau descend sous les seuils critiques.
* **Personnalisation complète** : Modification des seuils de couleurs, de la fréquence d'actualisation et gestion du lancement au démarrage directement depuis le menu contextuel.

### 📸 Aperçu

![Interface en Français 1](images/Keychron%20App%20FR1.png)

![Interface en Français 2](images/Keychron%20App%20FR2.png)

![Interface en Français 2](images/Keychron%20App%20FR3.png)

### 📦 Installation
1. Téléchargez la dernière version de l'installeur depuis l'onglet *Releases* du dépôt.
2. Double-cliquez sur le fichier pour lancer l'assistant d'installation.
3. L'application se configure et vous propose d'activer le lancement automatique au démarrage de Windows.

### 🛡️ Note concernant les antivirus (Faux Positif)
Lors de l'installation ou de l'exécution, **Windows Defender** ou certains antivirus peuvent afficher une alerte.
* **Pourquoi ?** Il s'agit d'un **faux positif** lié à l'interaction de bas niveau avec les flux matériels USB/HID (le script n'ayant pas de certificat de signature numérique payant).
* **Que faire ?** Le code source est entièrement ouvert et auditable. Il vous suffit d'ajouter le dossier de l'application aux **exclusions** de votre antivirus.

---

## English

**Keychron M3 Battery Monitor** is a lightweight and elegant Windows utility designed specifically to monitor the battery level of your **Keychron M3** mouse (via the USB dongle) directly from the system tray.

> 💡 *Developed by [Jessy JONKISZ](https://x.com/JNKZJessy)*
>
> ![Icône de l'application](images/Keychron%20App%20ico.png)

### 🚀 Features
* **Native HID Communication**: Direct hardware data extraction without heavy vendor software.
* **Clean & Professional UI**: 4 visual icon styles (Clean circle, Solid circle, Horizontal battery, Vertical battery) with dynamic color coding.
* **Advanced Statistics & Chart**:
  * Dedicated pop-up window with visual battery tracking.
  * 24h+ timeline axis structured in fixed 2-hour intervals.
  * **Smart Graphing**: Continuous solid green line for regular readings and orange dashed lines for estimated off-grid periods (e.g., when the PC or mouse was powered off).
* **Battery Life Estimation**: Smart time-remaining calculations based on historical usage.
* **Low Battery Alerts**: Native Windows notifications when the battery drops below critical levels.
* **Full Customization**: Easily change color thresholds, polling intervals, and startup behavior straight from the tray menu.

### 📸 Preview
![Interface en Français 1](images/Keychron%20App%20EN1.png)

![Interface en Français 2](images/Keychron%20App%20EN2.png)

![Interface en Français 2](images/Keychron%20App%20EN3.png)

### 📦 Installation
1. Download the latest installer from the *Releases* section of the repository.
2. Double-click the file to run the installation wizard.
3. The app installs and lets you configure your startup preferences easily.

### 🛡️ Antivirus Notice (False Positive)
During installation, **Windows Defender** or other security software may flag the executable.
* **Why?** This is a **false positive** triggered because the app interacts directly with low-level USB/HID hardware and lacks a commercial code-signing certificate.
* **What to do?** The source code is 100% open and reviewable. Simply add the application folder to your antivirus **exclusions list**.

---

### 📝 License
Distributed under the MIT License. See `LICENSE` for more information.
