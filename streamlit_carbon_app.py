"""
Streamlit app: Calculateur d'empreinte carbone d'entreprise

Fonctionnalités :
- Permet d'uploader une facture (PDF, CSV ou texte) ou coller son texte
- Envoie le texte/les lignes à 2 APIs (API_FACTURE, API_FACTEUR) — faux endpoints à remplacer
  * API_FACTURE : extrait les lignes de facture et renvoie une liste d'articles
  * API_FACTEUR : renvoie le facteur d'émission pour un produit donné (kgCO2e / unité)
- Calcule l'empreinte carbone par ligne et total
- Affiche tableau, graphique, résumé et permet de télécharger les résultats

Remplacer les constantes API_FACTURE_URL et API_FACTEUR_URL par vos vraies API.
Ne jamais exposer les clés API dans le front-end public.
"""

import streamlit as st
import requests
import pandas as pd
import io
import json
from typing import List, Dict, Any
import PyPDF2  # <-- NOUVEAU : Import de la bibliothèque PDF

# --------------------------- CONFIG ---------------------------
API_FACTURE_URL = "https://api1.example.com/parse_invoice"
API_FACTEUR_URL = "https://api2.example.com/emission_factor"
API_KEY = ""

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"} if API_KEY else {"Content-Type": "application/json"}

# --------------------------- HELPERS ---------------------------

# NOUVEAU : Fonction pour extraire le texte d'un PDF
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte brut d'un fichier PDF.
    Ne fonctionne pas sur les PDF qui sont des images scannées (nécessite un OCR).
    """
    try:
        pdf_file_obj = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file_obj)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        if not text.strip():
            st.warning("Le PDF semble vide ou est une image. L'extraction de texte n'a renvoyé aucun contenu.")
        return text
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la lecture du fichier PDF : {e}")


def call_api_invoice(text: str) -> List[Dict[str, Any]]:
    """Envoie le texte de la facture à API_FACTURE_URL et récupère la liste d'articles."""
    payload = {"invoice_text": text}
    try:
        resp = requests.post(API_FACTURE_URL, headers=HEADERS, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items")
        if items is None:
            raise ValueError("La réponse de l'API ne contient pas 'items'.")
        return items
    except Exception as e:
        raise RuntimeError(f"Erreur lors de l'appel à l'API facture: {e}")


def call_api_factor(product_description: str) -> Dict[str, Any]:
    """Appelle l'API des facteurs d'émission pour un produit donné."""
    payload = {"query": product_description}
    try:
        resp = requests.post(API_FACTEUR_URL, headers=HEADERS, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"Erreur lors de l'appel à l'API facteur: {e}")


def parse_csv_invoice(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Parse un CSV simple."""
    df = pd.read_csv(io.BytesIO(file_bytes))
    items = []
    # ... (le reste de la fonction est inchangé)
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if 'desc' in lc or 'product' in lc or 'label' in lc: col_map['description'] = c
        if 'qty' in lc or 'quantity' in lc: col_map['quantity'] = c
        if 'unit_price' in lc or 'price' in lc or 'pu' in lc: col_map['unit_price'] = c
        if 'unit' in lc: col_map['unit'] = c
    for _, row in df.iterrows():
        item = {
            'description': str(row[col_map.get('description', df.columns[0])]) if len(df.columns) > 0 else 'item',
            'quantity': float(row[col_map.get('quantity', df.columns[1])]) if 'quantity' in col_map or len(df.columns) > 1 else 1.0,
            'unit': str(row[col_map.get('unit', '')]) if 'unit' in col_map else 'unit',
            'unit_price': float(row[col_map.get('unit_price', df.columns[-1])]) if 'unit_price' in col_map or len(df.columns) > 1 else 0.0,
        }
        items.append(item)
    return items


def compute_carbon(items: List[Dict[str, Any]], use_api_for_factors: bool=True) -> pd.DataFrame:
    """Pour chaque item, récupère le facteur et calcule l'empreinte."""
    rows = []
    # ... (le reste de la fonction est inchangé)
    for i, it in enumerate(items):
        desc = it.get('description', '')
        qty = float(it.get('quantity', 1.0) or 1.0)
        unit = it.get('unit', '')
        unit_price = float(it.get('unit_price', 0.0) or 0.0)
        factor, factor_unit, note = None, 'kgCO2e/unit', ''
        if use_api_for_factors:
            try:
                f_resp = call_api_factor(desc)
                factor, factor_unit, note = float(f_resp.get('factor', 0.0)), f_resp.get('unit', factor_unit), f_resp.get('note', '') or ''
            except Exception as e:
                note, factor = f"fallback: {e}", fallback_factor_estimate(desc)
        else:
            factor = fallback_factor_estimate(desc)
        carbon_kg = qty * factor
        rows.append({'description': desc, 'quantity': qty, 'unit': unit, 'unit_price': unit_price, 'factor': factor, 'factor_unit': factor_unit, 'carbon_kg': carbon_kg, 'note': note})
    df = pd.DataFrame(rows)
    return df


def fallback_factor_estimate(description: str) -> float:
    """Estimation très simple de facteur d'émission."""
    desc = description.lower()
    # ... (le reste de la fonction est inchangé)
    if any(k in desc for k in ['electric', 'électricité', 'electricité']): return 0.05
    if any(k in desc for k in ['petrol', 'essence', 'diesel']): return 2.3
    if any(k in desc for k in ['steel', 'acier']): return 1.8
    if any(k in desc for k in ['paper', 'papier']): return 0.5
    return 0.1

# --------------------------- STREAMLIT UI ---------------------------

st.set_page_config(page_title="Calculateur Empreinte Carbone - Factures", layout='wide')
st.title("Calculateur d'empreinte carbone d'entreprise")
st.markdown("Upload une facture (**PDF**, CSV ou texte), ou colle le texte de la facture. L'application va extraire les lignes via une API, récupérer les facteurs d'émission via une autre API, et calculer le total.")

# ... (Sidebar inchangée)
with st.sidebar:
    st.header("Configuration API")
    st.text_input("API Facture URL", value=API_FACTURE_URL, key='api_facture_url')
    st.text_input("API Facteur URL", value=API_FACTEUR_URL, key='api_facteur_url')
    st.text_input("API Key (optionnel)", value=API_KEY, key='api_key', type='password')
    st.checkbox("Utiliser l'API pour facteurs (si décoché, usage du fallback)", value=True, key='use_api_factors')
    st.markdown("---")
    st.markdown("**Instructions:** Remplacez les URLs par vos endpoints réels. Ne mettez pas de clé API publique dans l'app si l'app est déployée publiquement.")

API_FACTURE_URL = st.session_state['api_facture_url']
API_FACTEUR_URL = st.session_state['api_facteur_url']
API_KEY = st.session_state['api_key']
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"} if API_KEY else {"Content-Type": "application/json"}

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Importer la facture")
    # MODIFIÉ : Ajout de 'pdf' aux types de fichiers acceptés
    uploaded_file = st.file_uploader("Fichier facture (PDF, CSV ou TXT)", type=['pdf', 'csv', 'txt'])
    invoice_text_area = st.text_area("Ou colle le texte brut de la facture (optionnel)", height=200)
    use_api_factors = st.session_state['use_api_factors']

    if st.button("Analyser la facture"):
        items = None
        invoice_text = ""
        try:
            if uploaded_file is not None:
                file_extension = uploaded_file.name.lower().split('.')[-1]
                
                # MODIFIÉ : Logique pour gérer les différents types de fichiers
                if file_extension == 'pdf':
                    invoice_text = extract_text_from_pdf(uploaded_file.read())
                    if invoice_text.strip():
                        items = call_api_invoice(invoice_text)
                elif file_extension == 'csv':
                    items = parse_csv_invoice(uploaded_file.read())
                else:  # Traiter comme du texte brut
                    invoice_text = uploaded_file.read().decode('utf-8')
                    items = call_api_invoice(invoice_text)
            
            elif invoice_text_area.strip():
                items = call_api_invoice(invoice_text_area)
            else:
                st.warning("Aucun fichier ni texte fourni.")

            if items is not None:
                with st.spinner("Récupération des facteurs et calculs..."):
                    df_results = compute_carbon(items, use_api_for_factors=use_api_factors)
                    st.session_state['last_results'] = df_results
                    st.success("Calcul terminé.")
        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {e}")

# ... (la colonne 2 pour les résultats reste inchangée)
with col2:
    st.subheader("Résultats")
    if 'last_results' in st.session_state:
        df = st.session_state['last_results']
        total_carbon = df['carbon_kg'].sum()
        total_cost = (df['quantity'] * df['unit_price']).sum() if 'unit_price' in df.columns else None
        st.metric(label="Empreinte totale (kg CO2e)", value=f"{total_carbon:,.2f}")
        if total_cost is not None:
            st.metric(label="Coût total", value=f"{total_cost:,.2f} (monnaie)")
        with st.expander("Tableau détaillé"):
            st.dataframe(df)
        st.subheader("Top contributeurs")
        top = df.sort_values('carbon_kg', ascending=False).head(10).set_index('description')
        if not top.empty:
            st.bar_chart(top['carbon_kg'])
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger les résultats (CSV)", data=csv_bytes, file_name='empreinte_facture.csv', mime='text/csv')
        st.subheader("Résumé par type d'unité de facteur")
        summary = df.groupby('factor_unit')['carbon_kg'].sum().reset_index()
        st.table(summary)
    else:
        st.info("Aucune analyse présente — importez une facture et cliquez sur 'Analyser la facture'.")

st.markdown("---")
st.caption("Ce prototype utilise deux endpoints fictifs (API_FACTURE_URL et API_FACTEUR_URL). Remplacez-les par vos vraies APIs. Le fallback heuristique est très approximatif.")