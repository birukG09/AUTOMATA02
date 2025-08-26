# AUTOMATA02 🚀

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)  
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)  
[![Streamlit](https://img.shields.io/badge/Streamlit-1.25.0-orange)](https://streamlit.io/)  

**AUTOMATA02** is an **intelligent workspace automation hub** that streamlines your file organization, monitors UI workflows, and automates reporting pipelines. It combines **smart file sorting**, **automation macros**, and **autonomous data reporting**, powered by Python, Pandas, Streamlit, and AI/ML-inspired logic.  

---

## ✨ Key Features

- **Intelligent File Sorting**
  - Automatic labeling, tagging, and classification of files.
  - Smart suggestions based on file patterns and content snippets.
  - Integration-ready for AI/ML text analysis.

- **UI Monitoring & Automation**
  - Capture repetitive GUI interactions for automation (via AutoKey or simulated logic).
  - Macro manager to create, test, and schedule automation tasks.
  - Workflow dashboards to monitor live progress and metrics.

- **Autonomous Reporting Pipeline**
  - Automatic generation of weekly or custom reports.
  - Filter by labels, tags, or metadata.
  - Simulated PDF/HTML export for reports.
  - Preview and history tracking for all reports.

- **Advanced Dashboard**
  - Data visualizations: trends, top labels, activity metrics.
  - Real-time updates (simulated for demo).
  - Metrics cards and interactive Plotly charts.

- **Custom Rules Engine**
  - YAML-based rules to automate file moves, labeling, and tagging.
  - Dry-run simulation mode for safe testing.
  - Extensible for future AI-assisted rule suggestions.

- **Modular Design**
  - Streamlit-powered frontend, pandas-powered backend.
  - Well-structured folder architecture: `core/`, `pages/`, `utils/`, `config/`.
  - Easy to extend with new automation features, macros, and dashboards.

---

## 🖥 Screenshots (Demo)

**Dashboard**  
![Dashboard Placeholder](https://via.placeholder.com/800x400.png?text=AUTOMATA02+Dashboard)  

**Inventory & File Management**  
![Inventory Placeholder](https://via.placeholder.com/800x400.png?text=Inventory+Page)  

**Rules Editor (YAML)**  
![Rules Editor](https://via.placeholder.com/800x400.png?text=Rules+Editor)  

**Macros Manager**  
![Macros Manager](https://via.placeholder.com/800x400.png?text=Macros+Manager)  

**Reports**  
![Reports Page](https://via.placeholder.com/800x400.png?text=Reports+Page)  

---

## 🛠 Installation

1. Clone the repo:
```bash
git clone https://github.com/birukG09/AUTOMATA02.git
cd AUTOMATA02/AUTOMATA02
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Run the app:

bash
Copy
Edit
streamlit run app.py
Open your browser at http://localhost:8501 to view the AUTOMATA02 dashboard.

📁 Folder Structure
graphql
Copy
Edit
AUTOMATA02/
│
├─ app.py                # Main Streamlit app
├─ requirements.txt      # Python dependencies
├─ sample_data.py        # Demo data generator
├─ core/                 # Core automation logic
├─ pages/                # Streamlit pages (Dashboard, Inventory, Rules...)
├─ utils/                # Helper functions
├─ config/               # Configuration files
├─ .streamlit/           # Streamlit settings
├─ style.css             # Custom CSS for UI theme
└─ uv.lock               # Lock file for reproducible environment
⚙️ Usage
Dashboard: Monitor overall activity, trends, and metrics.

Inventory: Browse and search files, preview, and tag.

Rules: Define YAML rules to automate file organization.

Macros: Schedule and simulate GUI automation tasks.

Reports: Build, preview, and schedule data reports.

Control Panel: Launch notebooks, check system health, and manage workers.

Note: Current version is demo/simulated. Real-time automation and live system integration can be added with watchdog + SQLite backend and macro execution.

🌟 Advanced Features Planned
Full watchdog-based file system monitoring with persistent SQLite DB.

AI/ML-driven macro suggestion using historical user behavior.

Visual Rule Builder: drag-and-drop interface.

Export reports to real PDF/HTML with templates.

Integration with FastAPI backend for RESTful access.

💡 Contribution
Contributions are welcome! Suggestions, bug reports, and feature requests can be submitted via GitHub Issues.
