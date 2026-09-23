# ActiveAge Lab — KINECAL Sway Explorer

Public-facing Streamlit app using supplied KINECAL CSV exports.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository and put this folder’s contents at the repository root.
2. At https://share.streamlit.io, choose **Create app** → **Yup, I have an app**.
3. Choose your repository, branch `main`, entrypoint `app.py`, and Python 3.12 in Advanced settings. No secrets are required.
4. Deploy. In the app’s **Share** settings, select **This app is public and searchable** and verify the resulting URL in a signed-out window.

Keep `data/` alongside `app.py`; the dashboard checks the six CSVs when it loads. All input records use the supplied exports; no model fitting happens at runtime.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

This dashboard provides measurement and statistical comparison of camera-derived postural sway. It is not a diagnostic tool and does not predict future falls.
