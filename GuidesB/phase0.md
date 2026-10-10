> Part of Guide B. See [`guide_B_app.md`](../guide_B_app.md) for the mission, dependencies and timeline.

## PHASE 0: Setup (H0:00 to H0:45)

**Objective:** a working Streamlit on your computer.

1. Install Python 3.10 or newer. Check: `python --version`.
2. Install the tools:
   ```
   pip install streamlit pandas numpy plotly anthropic
   ```
3. Make a file `hello.py` with:
   ```python
   import streamlit as st
   st.title("It works")
   ```
4. Run `streamlit run hello.py`. A browser tab should open showing "It works". (Delete `hello.py` afterwards.)
5. Get the repo from D (about H0:20) and pull the files.

**If stuck:** if `streamlit` is not found, use `python -m streamlit run hello.py`. If the browser does not open, copy the link (like http://localhost:8501) from the terminal into the browser.
