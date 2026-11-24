from pathlib import Path

import streamlit as st


DOSSIER_ASSETS = Path(__file__).parent.parent / "assets"


def lire_asset(extension):
    return (DOSSIER_ASSETS / f"salle_3d.{extension}").read_text(encoding="utf-8")


salle_3d = st.components.v2.component("salle_3d", html=lire_asset("html"), css=lire_asset("css"), js=lire_asset("js"))
