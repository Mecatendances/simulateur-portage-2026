"""python test_pdf.py : rendu réel WeasyPrint, sans écraser les PDF du dépôt."""
import os
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from jinja2 import Template
from weasyprint import HTML

from test_calcul import g, run

app = Path(__file__).with_name("app.py")
source = app.read_text()
g.update(__file__=str(app), os=os, tempfile=tempfile, plt=plt, Template=Template, HTML=HTML)
exec(source[source.index("# --- Chemin logo ---"):source.index("# --- UI Streamlit ---")], g)
contact = {"name": "Équipe de test", "title": "Conseil", "email": "test@example.test",
           "phone": "01 00 00 00 00", "mobile": ""}


def html_verifie(string):
    assert "&lt;em&gt;" in string and "<em>" not in string, "Le nom doit être échappé"
    return HTML(string=string)


g["HTML"] = html_verifie
for contrat, reserve in (("CDI", True), ("CDI", False), ("CDD", True)):
    data = run(500, type_contrat=contrat, use_reserve=reserve)
    pdf = g["create_pdf"](data, "Alice <em>Test</em>", contact)
    assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-20:]
    assert len(pdf) > 1000
    print(f"OK : PDF {contrat}, réserve provisionnée={reserve}, {len(pdf)} octets")
