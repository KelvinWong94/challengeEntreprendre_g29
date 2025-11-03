"""
Streamlit app: Calculateur d'empreinte carbone d'entreprise (Version Écologique)

Fonctionnalités :
- Permet d'uploader un ou plusieurs fichiers de facture (PDF, CSV ou texte)
- Envoie le texte/les lignes à 2 APIs (API_FACTURE, API_FACTEUR) — faux endpoints à remplacer
- Calcule l'empreinte carbone par ligne et total pour l'ensemble des factures
- Affiche tableau, graphique, résumé et permet de télécharger les résultats
"""

import streamlit as st
import requests
import pandas as pd
import io
import json
from typing import List, Dict, Any
import PyPDF2
import time # <-- NOUVEAU : Pour simuler un chargement plus visible

# --------------------------- CONFIG ---------------------------
API_FACTURE_URL = "https://api1.example.com/parse_invoice"
API_FACTEUR_URL = "https://api2.example.com/emission_factor"
API_KEY = ""
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"} if API_KEY else {"Content-Type": "application/json"}

# --------------------------- HELPERS ---------------------------
# Les fonctions helpers restent inchangées.
def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        pdf_file_obj = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file_obj)
        text = ""
        for page in pdf_reader.pages: text += page.extract_text() + "\n"
        if not text.strip(): st.warning("Le PDF semble vide ou est une image. L'extraction de texte n'a renvoyé aucun contenu.")
        return text
    except Exception as e: raise RuntimeError(f"Erreur lors de la lecture du fichier PDF : {e}")
def call_api_invoice(text: str) -> List[Dict[str, Any]]:
    payload = {"invoice_text": text}
    try:
        resp = requests.post(API_FACTURE_URL, headers=HEADERS, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items")
        if items is None: raise ValueError("La réponse de l'API ne contient pas 'items'.")
        return items
    except Exception as e: raise RuntimeError(f"Erreur lors de l'appel à l'API facture: {e}")
def call_api_factor(product_description: str) -> Dict[str, Any]:
    payload = {"query": product_description}
    try:
        resp = requests.post(API_FACTEUR_URL, headers=HEADERS, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e: raise RuntimeError(f"Erreur lors de l'appel à l'API facteur: {e}")
def parse_csv_invoice(file_bytes: bytes) -> List[Dict[str, Any]]:
    df = pd.read_csv(io.BytesIO(file_bytes))
    items = []
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if 'desc' in lc or 'product' in lc: col_map['description'] = c
        if 'qty' in lc or 'quantity' in lc: col_map['quantity'] = c
        if 'unit_price' in lc or 'price' in lc: col_map['unit_price'] = c
        if 'unit' in lc: col_map['unit'] = c
    for _, row in df.iterrows():
        items.append({'description': str(row[col_map.get('description', df.columns[0])]), 'quantity': float(row[col_map.get('quantity', df.columns[1])]),'unit': str(row[col_map.get('unit', '')]),'unit_price': float(row[col_map.get('unit_price', df.columns[-1])]),})
    return items
def compute_carbon(items: List[Dict[str, Any]], use_api_for_factors: bool=True) -> pd.DataFrame:
    rows = []
    progress_bar = st.progress(0, text="Calcul des empreintes...")
    for i, it in enumerate(items):
        desc, qty, unit, unit_price = it.get('description', ''), float(it.get('quantity', 1.0) or 1.0), it.get('unit', ''), float(it.get('unit_price', 0.0) or 0.0)
        factor, factor_unit, note = None, 'kgCO2e/unit', ''
        if use_api_for_factors:
            try:
                f_resp = call_api_factor(desc)
                factor, factor_unit, note = float(f_resp.get('factor', 0.0)), f_resp.get('unit', factor_unit), f_resp.get('note', '') or ''
            except Exception as e: note, factor = f"fallback: {e}", fallback_factor_estimate(desc)
        else: factor = fallback_factor_estimate(desc)
        carbon_kg = qty * factor
        rows.append({'description': desc, 'quantity': qty, 'unit': unit, 'unit_price': unit_price, 'factor': factor, 'factor_unit': factor_unit, 'carbon_kg': carbon_kg, 'note': note})
        progress_bar.progress((i + 1) / len(items), text=f"Calcul en cours pour : {desc[:30]}...")
    progress_bar.empty()
    return pd.DataFrame(rows)
def fallback_factor_estimate(description: str) -> float:
    desc = description.lower()
    if any(k in desc for k in ['electric', 'électricité']): return 0.05
    if any(k in desc for k in ['petrol', 'essence', 'diesel']): return 2.3
    if any(k in desc for k in ['steel', 'acier']): return 1.8
    if any(k in desc for k in ['paper', 'papier']): return 0.5
    return 0.1

# --------------------------- STREAMLIT UI ---------------------------

# <-- NOUVEAU : Configuration de la page avec un thème personnalisé et une icône
st.set_page_config(
    page_title="Eco-Bilan Carbone",
    page_icon="🌿",
    layout='wide',
    initial_sidebar_state='expanded'
)

# <-- NOUVEAU : Injection de CSS pour des styles plus fins si nécessaire (optionnel)
st.markdown("""
<style>
    /* Modifier la couleur des headers dans la sidebar */
    [data-testid="stSidebar"] .st-emotion-cache-10oheav h1 {
        color: #0A6847; /* Vert foncé */
    }
    /* Style des boutons */
    .stButton>button {
        border-radius: 50px;
        background-color: #7ABA78; /* Vert moyen */
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0A6847; /* Vert foncé au survol */
        color: white;
        border: none;
    }
</style>
""", unsafe_allow_html=True)


# --- SIDEBAR ---
with st.sidebar:
    # <-- NOUVEAU : Ajout d'un logo
    # Remplacez l'URL par le chemin local de votre image: "assets/logo.png"
    st.image("https://i.imgur.com/vRhS9Db.png", width=100)
    st.title("Eco-Bilan Carbone")

    st.header("⚙️ Configuration API")
    st.text_input("API Facture URL", value=API_FACTURE_URL, key='api_facture_url')
    st.text_input("API Facteur URL", value=API_FACTEUR_URL, key='api_facteur_url')
    st.text_input("API Key (optionnel)", value=API_KEY, key='api_key', type='password')
    st.checkbox("Utiliser l'API pour les facteurs", value=True, key='use_api_factors')
    st.markdown("---")
    st.info("Cette application est un prototype. Les facteurs d'émission sont des estimations.")

API_FACTURE_URL = st.session_state['api_facture_url']
API_FACTEUR_URL = st.session_state['api_facteur_url']
API_KEY = st.session_state['api_key']
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"} if API_KEY else {"Content-Type": "application/json"}

# --- MAIN PAGE ---
st.title("🌳 Calculateur d'empreinte carbone d'entreprise")
st.markdown("Uploadez une ou plusieurs factures (PDF, CSV, TXT) pour analyser leur empreinte carbone combinée.")

col1, col2 = st.columns([1, 2])

with col1:
    # <-- NOUVEAU : Utilisation d'un container pour un meilleur design
    with st.container(border=True):
        st.subheader("📤 Importez vos factures")
        uploaded_files = st.file_uploader(
            "Sélectionnez un ou plusieurs fichiers",
            type=['pdf', 'csv', 'txt'],
            accept_multiple_files=True
        )

        use_api_factors = st.session_state['use_api_factors']

        if st.button("♻️ Lancer l'analyse", use_container_width=True):
            if uploaded_files:
                all_items = []
                processing_placeholder = st.empty()
                try:
                    for uploaded_file in uploaded_files:
                        processing_placeholder.info(f"Traitement du fichier : `{uploaded_file.name}`...")
                        items = []
                        file_extension = uploaded_file.name.lower().split('.')[-1]
                        
                        if file_extension == 'pdf':
                            invoice_text = extract_text_from_pdf(uploaded_file.read())
                            if invoice_text.strip(): items = call_api_invoice(invoice_text)
                        elif file_extension == 'csv': items = parse_csv_invoice(uploaded_file.read())
                        else: items = call_api_invoice(uploaded_file.read().decode('utf-8'))
                        
                        if items: all_items.extend(items)
                    
                    processing_placeholder.empty()

                    if all_items:
                        df_results = compute_carbon(all_items, use_api_for_factors=use_api_factors)
                        st.session_state['last_results'] = df_results
                        st.success(f"Analyse terminée pour {len(uploaded_files)} facture(s).")
                        time.sleep(1) # Laisse le temps de lire le message
                        st.rerun() # Rafraîchit la page pour afficher les résultats proprement
                    else:
                        st.warning("Aucun article n'a pu être extrait des fichiers fournis.")

                except Exception as e:
                    st.error(f"Erreur lors de l'analyse: {e}")
            else:
                st.warning("Veuillez uploader au moins un fichier.")

with col2:
    # <-- NOUVEAU : Conteneur pour la zone de résultats
    with st.container(border=True):
        st.subheader("📊 Résultats combinés")
        if 'last_results' in st.session_state and not st.session_state['last_results'].empty:
            df = st.session_state['last_results']
            total_carbon = df['carbon_kg'].sum()
            total_cost = (df['quantity'] * df['unit_price']).sum() if 'unit_price' in df.columns else None

            # Métriques
            mcol1, mcol2 = st.columns(2)
            mcol1.metric(label="Empreinte Totale (kg CO2e)", value=f"{total_carbon:,.2f}")
            if total_cost:
                mcol2.metric(label="Coût Total Estimé", value=f"{total_cost:,.2f} €")

            # Graphique
            st.markdown("##### 📈 Top 10 des contributeurs")
            top = df.sort_values('carbon_kg', ascending=False).head(10).set_index('description')
            if not top.empty:
                st.bar_chart(top['carbon_kg'], color="#7ABA78") # <-- NOUVEAU : Couleur personnalisée

            # Tableau détaillé
            with st.expander("Voir le tableau détaillé des calculs"):
                st.dataframe(df)
            
            # Bouton de téléchargement
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Télécharger les résultats (CSV)", data=csv_bytes, file_name='bilan_carbone.csv', mime='text/csv', use_container_width=True)
        else:
            # <-- NOUVEAU : Message d'accueil visuel
            st.image("https://i.imgur.com/uX1ECc5.png") # Image placeholder
            st.info("Vos résultats s'afficheront ici une fois l'analyse terminée.")