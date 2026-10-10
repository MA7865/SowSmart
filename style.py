"""Look-and-feel only for the SowSmart Streamlit app."""
import html
import re

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: linear-gradient(180deg, #ffffff 0%, #f4f8f1 100%);
    color: #121812;
}
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp button, .stApp input, .stApp textarea, .stApp td, .stApp th,
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"] {
    font-family: 'Inter', 'Noto Naskh Arabic', system-ui, sans-serif;
    color: #121812;
}
.stApp p, .stApp li, .stApp label {
    font-size: 1.1rem;
    line-height: 1.65;
    font-weight: 500;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    color: #121812;
    font-weight: 700;
}
.stApp h2, .stApp h3 {
    background: none;
    border: none;
    box-shadow: none;
    padding: 0;
    margin-top: 2rem;
    margin-bottom: 0.75rem;
    font-size: 1.6rem;
    line-height: 1.35;
}
.stApp h2 {
    border-bottom: 3px solid #285d36;
    padding-bottom: 0.35rem;
}
.stApp div[data-testid="stHeading"] {
    background: none;
    border: none;
    box-shadow: none;
    padding: 0;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color: #121812;
    font-size: 0.95rem;
    line-height: 1.65;
    font-weight: 500;
    opacity: 1;
}
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1100px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}
footer { visibility: hidden; }
.stApp [data-testid="stVerticalBlock"] > div { margin-bottom: 0.5rem; }

.urdu {
    direction: rtl;
    text-align: right;
    font-family: 'Noto Naskh Arabic', serif;
    font-size: 1.3rem;
    line-height: 2.1;
    color: #121812;
    margin: 0.25rem 0 0.75rem;
}
.urdu ul { padding-right: 1.25rem; padding-left: 0; margin: 0; }
.urdu li { margin-bottom: 0.4rem; font-size: 1.3rem; line-height: 2.1; }

.brand-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 0 0 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 3px solid #285d36;
}
.brand-logo { width: 88px; height: 88px; object-fit: contain; flex: 0 0 auto; }
.brand-name { color: #285d36; font-size: 2.5rem; font-weight: 800; line-height: 1.15; }
.brand-subtitle { color: #121812; font-size: 1.1rem; margin-top: 0.25rem; opacity: 1; font-weight: 500; }

button[data-baseweb="tab"] {
    padding: 0.75rem 1rem;
    height: auto;
    margin-right: 0.5rem;
    border: 1.5px solid #285d36;
    border-radius: 8px;
    background: #ffffff;
}
button[data-baseweb="tab"] p {
    color: #121812;
    font-size: 1.05rem;
    font-weight: 700;
}
button[data-baseweb="tab"][aria-selected="true"] { background: #285d36; }
button[data-baseweb="tab"][aria-selected="true"] p { color: #ffffff; }
[data-baseweb="tab-list"] { gap: 0.5rem; border-bottom: none; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }

[data-testid="stMetric"] {
    min-height: 8rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    border: 2px solid #285d36;
    border-left: 8px solid #285d36;
    border-radius: 10px;
    padding: 1.25rem;
    background: #ffffff;
    box-shadow: none;
}
[data-testid="stMetric"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    border: none;
    box-shadow: none;
    background: none;
}
[data-testid="stMetricLabel"] p {
    color: #121812;
    font-size: 0.95rem;
    line-height: 1.45;
    font-weight: 500;
    white-space: normal;
}
[data-testid="stMetricValue"] {
    color: #121812;
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1.35;
}
[data-testid="stMetricValue"] > div {
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
}

[data-testid="stDataFrame"], [data-testid="stTable"], [data-testid="stPlotlyChart"],
[data-testid="stArrowVegaLiteChart"], [data-testid="stVegaLiteChart"],
[data-testid="stAlert"], [data-testid="stSidebar"] {
    border: 1.5px solid #285d36;
    border-left: 6px solid #285d36;
    border-radius: 10px;
    padding: 1rem;
    background: #ffffff;
    box-shadow: none;
}
[data-testid="stAlert"] { padding: 1.25rem; }
[data-testid="stDataFrame"] *, [data-testid="stTable"] *,
[data-testid="stPlotlyChart"] *, [data-testid="stArrowVegaLiteChart"] *,
[data-testid="stVegaLiteChart"] *, [data-testid="stAlert"] *,
[data-testid="stSidebar"] * {
    box-shadow: none;
    background-image: none;
}
[data-testid="stDataFrame"] th, [data-testid="stTable"] th {
    background: #eef5ea;
    color: #121812;
    font-weight: 700;
}
[data-testid="stDataFrame"] td, [data-testid="stTable"] td {
    color: #121812;
    font-size: 1rem;
}

.stSelectbox label p, .stSlider label p, .stTextInput label p {
    color: #121812;
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}
.stSelectbox [data-baseweb="select"] > div, .stTextInput input {
    border: 2px solid #285d36;
    border-radius: 10px;
    background: #ffffff;
    color: #121812;
    font-size: 1.05rem;
}
.stSlider [data-baseweb="slider"] {
    border: none;
    background: none;
}

@media (max-width: 640px) {
    .brand-name { font-size: 1.9rem; }
    .brand-logo { width: 64px; height: 64px; }
    .urdu, .urdu li { font-size: 1.3rem; }
    [data-testid="stMetricValue"] { font-size: 1.9rem; }
}
</style>
"""


def inject_css():
    """Call once, right after st.set_page_config()."""
    st.markdown(CSS, unsafe_allow_html=True)


def urdu_html(text):
    """Safe HTML for Urdu text. Turns **bold** and '- ' lines into real
    bold and bullets (st.markdown does not do this inside a <div>)."""
    out, in_list = [], False
    for line in html.escape(text).split("\n"):
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(line + "<br>")
    if in_list:
        out.append("</ul>")
    return "".join(out)
