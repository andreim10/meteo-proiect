"""Mici utilitare pentru tabele (folosite de toate tab-urile)."""
from tkinter import ttk


def tabel(parent, coloane, inaltime=8):
    """Creează un Treeview. coloane = [(id, titlu, lățime), ...]"""
    t = ttk.Treeview(parent, columns=[c[0] for c in coloane], show="headings", height=inaltime)
    for cid, titlu, lat in coloane:
        t.heading(cid, text=titlu)
        t.column(cid, width=lat, anchor="center")
    return t


def umple(t, randuri):
    t.delete(*t.get_children())
    for r in randuri:
        t.insert("", "end", values=r)
