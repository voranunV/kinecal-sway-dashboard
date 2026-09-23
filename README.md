# ActiveAge Lab — KINECAL Sway Explorer

A Streamlit dashboard built from the supplied KINECAL CSV exports. The app reads the six CSV files in `data/`; it does not retrain models or produce new predictions. The existing public deployment is [on Render](https://activeage-lab-kinecal-sway-explorer.onrender.com/).

## Run locally on the Mac

The project folder is `AgeTech_Fall_Risk_Capstone/dashboard`. The existing virtual environment in `AgeTech_Fall_Risk_Capstone/.venv` uses Python 3.10.11. From the parent project folder in VS Code Terminal:

```bash
cd dashboard
source ../.venv/bin/activate
python --version
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL shown by Streamlit (usually http://localhost:8501). Stop the server with Ctrl+C. For subsequent runs, activate the environment and run the final command again.

`requirements.txt` selects NumPy 2.2.6 for Python 3.10 and NumPy 2.3.5 for Python 3.11 or newer. You do not need to edit dependency versions when switching between these Python versions.

## GitHub and Render

This GitHub repository contains the contents of `dashboard/` at the repository root. Work on the local `dashboard` Git repository when updating the public app; the parent `AgeTech_Fall_Risk_Capstone` Git repository is separate. The Render service deploys the dashboard from this repository's `main` branch.

Keep `app.py`, `data_access.py`, `requirements.txt`, `.streamlit/config.toml`, and the six bundled CSVs in `data/` together. Changes to documentation or dependencies can also trigger a Render deployment.

## Scope

The dashboard shows descriptive movement measurements and the statistical references supplied in the CSV exports. It does not rerun the notebooks, refit models, diagnose a condition, or predict future falls.
