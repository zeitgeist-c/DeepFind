"""Programmatic search uses the same semantic engine as the GUI."""
from .rank import search_semantic

def search(con,query,limit=50,**kwargs):
    return search_semantic(con,query,limit=limit,**kwargs)["results"]
