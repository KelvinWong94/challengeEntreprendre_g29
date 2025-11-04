import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(
    page_title="Analyse Carbone par IA",
    page_icon="logo.png",  # Vous pouvez aussi utiliser votre logo comme icône d'onglet
    layout="wide"
)

# --- EN-TÊTE AVEC LOGO ET TITRE ---
col1, col2 = st.columns([1, 6]) # Crée 2 colonnes, la 2ème est 6 fois plus large

with col1:
    st.image("logo.png", width=120) # Affichez votre logo ici, ajustez la largeur si besoin

with col2:
    st.title("Tableau de Bord d'Analyse Carbone par IA")
    st.markdown("Uploadez vos factures PDF pour analyser et visualiser leur empreinte carbone.")

# Le reste de votre code continue ici...


# --- CONFIGURATION DE L'API GEMINI (SIDEBAR) ---
with st.sidebar:
    st.header("🔑 Configuration de l'API")
    st.markdown("Pour utiliser cette application, veuillez fournir votre clé API Google Gemini.")
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("Clé API chargée depuis les secrets.", icon="✅")
    except (FileNotFoundError, KeyError):
        api_key = st.text_input("Entrez votre clé API Gemini", type="password", help="Votre clé ne sera pas stockée.")

    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("API Gemini configurée avec succès !", icon="🚀")
        except Exception as e:
            st.error(f"Erreur de configuration de l'API: {e}")
    else:
        st.warning("Veuillez entrer une clé API pour continuer.")

# --- FONCTIONS DE TRAITEMENT ET D'ANALYSE ---

@st.cache_data
def load_ademe_data(filepath: str = "base-carbone.csv") -> Optional[pd.DataFrame]:
    """Charge les données de la Base Carbone de l'ADEME depuis un fichier CSV."""
    try:
        df = pd.read_csv(filepath, sep=';', encoding='cp1252')
        required_cols = ['Nom base français', 'Total poste non décomposé', 'Unité français']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Colonnes manquantes dans le fichier CSV : {', '.join(missing_cols)}")
            return None
            
        df['Total poste non décomposé'] = pd.to_numeric(df['Total poste non décomposé'].str.replace(',', '.'), errors='coerce')
        df.dropna(subset=['Total poste non décomposé'], inplace=True)
        st.success("Base Carbone® de l'ADEME chargée avec succès.")
        return df
        
    except FileNotFoundError:
        st.warning(f"Le fichier `{filepath}` n'a pas été trouvé. L'analyse se basera uniquement sur l'IA.")
        return None
    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement du fichier ADEME : {e}")
        return None

@st.cache_data
def get_structured_info_from_llm(description: str) -> Optional[Dict[str, Any]]:
    """Utilise l'IA pour extraire les mots-clés ET l'unité d'une description."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"""
    Analyse la description de facture suivante : "{description}"
    Extrais les informations suivantes :
    1. 'keywords': Une liste de 2-4 mots-clés génériques décrivant le produit/service.
    2. 'unit': L'unité la plus pertinente mentionnée ou implicite (ex: 'm²', 'kg', 'jour', 'unité', 'trajet', 'licence'). Si aucune unité n'est claire, retourne 'unité'.

    Réponds UNIQUEMENT avec un objet JSON.
    Exemple pour "Réservation d'un stand de 6 m²" : {{"keywords": ["stand", "salon", "exposition"], "unit": "m²"}}
    Exemple pour "Billet de train Paris-Lyon" : {{"keywords": ["train", "transport", "voyageur"], "unit": "trajet"}}
    """
    try:
        response = model.generate_content(prompt)
        json_match = re.search(r'\{[\s\S]*\}', response.text)
        if json_match:
            return json.loads(json_match.group(0))
        return None
    except Exception:
        return None

def search_ademe_base_carbone(keywords: List[str], ademe_df: pd.DataFrame) -> Optional[pd.Series]:
    """Recherche dans la Base Carbone et retourne la meilleure ligne correspondante (objet pd.Series)."""
    if ademe_df is None or not keywords: return None

    best_match_row = None
    max_score = 0
    search_terms = set(k.lower() for k in keywords)
    name_col = 'Nom base français'
    
    for index, row in ademe_df.iterrows():
        product_name_terms = set(re.findall(r'\w+', str(row[name_col]).lower()))
        score = len(search_terms.intersection(product_name_terms))
        if score > max_score:
            max_score = score
            best_match_row = row
    
    min_required_score = max(1, len(search_terms) // 2)
    if max_score >= min_required_score:
        return best_match_row
    return None

### MODIFIÉ : La fonction de validation devient un "Juge Expert" ###
@st.cache_data
def are_units_compatible(description: str, invoice_unit: str, ademe_unit: str) -> bool:
    """
    Demande à l'IA de juger, en tant qu'expert, si les unités sont mathématiquement
    compatibles POUR LE PRODUIT SPÉCIFIQUE en question.
    """
    if invoice_unit.lower().replace(" ", "") == ademe_unit.lower().replace(" ", ""):
        return True
        
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"""
    Tu es un auditeur expert en calcul carbone. Tu dois valider une opération mathématique.

    CONTEXTE :
    - Produit sur la facture : "{description}"
    - L'unité de ce produit est : "{invoice_unit}"
    - Un facteur d'émission a été trouvé dans une base de données avec l'unité : "kgCO2e / {ademe_unit}"

    TA MISSION :
    Détermine si l'opération suivante est mathématiquement et physiquement correcte :
    (Quantité en '{invoice_unit}') * (Facteur en 'kgCO2e / {ademe_unit}') = Empreinte Carbone en kgCO2e ?

    RAISONNEMENT À SUIVRE :
    1.  Analyse l'unité de la facture. Est-ce une surface, un poids, un temps, un service unitaire ?
    2.  Analyse l'unité de la base de données.
    3.  Pour le produit "{description}", sont-elles interchangeables ?
        - EXEMPLE DE BONNE COMPATIBILITÉ : Pour un "Billet de train", l'unité 'trajet' (facture) est compatible avec 'passager.km' (base de données) car un trajet a une distance implicite.
        - EXEMPLE DE MAUVAISE COMPATIBILITÉ : Pour un "Stand de 6 m²", l'unité 'm²' (facture) n'est PAS compatible avec 'jour' ou 'événement' (base de données), car on ne peut pas multiplier une surface par un facteur temporel pour obtenir un impact carbone.

    Réponds UNIQUEMENT avec un objet JSON : {{"compatible": true}} ou {{"compatible": false}}.
    """
    try:
        response = model.generate_content(prompt)
        json_match = re.search(r'\{[\s\S]*\}', response.text)
        if json_match:
            return json.loads(json_match.group(0)).get("compatible", False)
        return False
    except Exception:
        return False

@st.cache_data
def extract_invoice_data_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """Extrait les données structurées d'un PDF."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    invoice_file = genai.upload_file(path=pdf_path, display_name=Path(pdf_path).name)
    prompt = """
    Tu es un système expert d'extraction de données de factures. Extrais les informations suivantes : le numéro de facture, le nom du vendeur, la date de la facture (YYYY-MM-DD), et une liste 'line_items'. Pour chaque article, je veux la description, la quantité et le prix total. Réponds UNIQUEMENT en JSON valide.
    """
    try:
        response = model.generate_content([prompt, invoice_file])
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
        cleaned_text = json_match.group(1) if json_match else response.text
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des données du PDF : {e}")
        return None
    finally:
        genai.delete_file(invoice_file.name)

@st.cache_data
def get_carbon_analysis_from_llm(description: str, quantity: float) -> Dict[str, Any]:
    """Analyse un article de facture pour estimer son empreinte carbone en utilisant une approche d'expert ACV."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"""
    Tu es un expert en Analyse de Cycle de Vie (ACV) spécialisé dans les achats d'entreprise.
    Ta mission est d'estimer l'empreinte carbone pour la ligne de facture suivante de la manière la plus réaliste et justifiée possible.

    Description de l'article : "{description}"
    Quantité facturée : {quantity}

    INSTRUCTIONS DÉTAILLÉES :
    1.  **Analyse Sémantique** : Lis la description. Identifie la nature exacte du produit/service et surtout les **unités et dimensions** (ex: "6 m²", "10 unités").
    2.  **Décomposition ACV** : Décompose le produit/service en ses sources d'émission principales. Pour un objet physique (stand, ordinateur...), considère **Matériaux, Logistique, Énergie, Fin de vie**. Pour un service (logiciel, billet de train...), considère **Énergie (serveurs, transport), Infrastructure amortie**.
    3.  **Calcul Final** : Calcule l'empreinte carbone **totale** en kgCO2e pour l'ensemble de la description. Puis, divise ce total par la "Quantité facturée" ({quantity}) pour obtenir le facteur par unité facturée. C'est cette valeur que tu dois retourner.
    4.  **Justification** : Ta justification doit expliquer ton calcul total et tes hypothèses chiffrées.

    Réponds UNIQUEMENT au format JSON.
    {{
      "category": "La catégorie d'émission la plus pertinente (ex: 'Événementiel - Stand et Structure')",
      "estimated_factor_kgCO2e_per_unit": <nombre flottant résultant de ton calcul>,
      "justification": "DÉTAIL DU CALCUL : Empreinte totale pour l'item = X kgCO2e. Répartition : [Détails de ta décomposition ACV]. Facteur retourné = X / {quantity}.",
      "confidence_score": <nombre flottant entre 0.0 et 1.0>
    }}
    """
    try:
        response = model.generate_content(prompt)
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
        cleaned_text = json_match.group(1) if json_match else response.text
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Erreur pendant l'analyse carbone pour '{description[:30]}...' : {e}")
        return None

# --- LOGIQUE PRINCIPALE DE L'APPLICATION ---
if 'results_df' not in st.session_state:
    st.session_state.results_df = pd.DataFrame()
ademe_df = load_ademe_data()

uploaded_files = st.file_uploader("Chargez une ou plusieurs factures au format PDF", type="pdf", accept_multiple_files=True)

if st.button("🚀 Lancer l'analyse", disabled=(not uploaded_files or not api_key), use_container_width=True):
    with st.spinner("Analyse en cours... Cette opération peut prendre quelques minutes."):
        temp_dir = Path("./temp_pdfs")
        temp_dir.mkdir(exist_ok=True)
        all_results = []
        progress_bar = st.progress(0, text="Initialisation...")
        
        for i, uploaded_file in enumerate(uploaded_files):
            pdf_path = temp_dir / uploaded_file.name
            with open(pdf_path, "wb") as f: f.write(uploaded_file.getbuffer())

            progress_text = f"Fichier {i+1}/{len(uploaded_files)} : Extraction des données..."
            progress_bar.progress((i + 0.1) / len(uploaded_files), text=progress_text)
            extracted_data = extract_invoice_data_from_pdf(str(pdf_path))
            
            if extracted_data and "line_items" in extracted_data:
                invoice_date = extracted_data.get("invoice_date")
                line_items = extracted_data["line_items"]

                for j, item in enumerate(line_items):
                    description = item.get('description', 'N/A')
                    progress_text = f"Fichier {i+1}/{len(uploaded_files)} : Analyse de '{description[:30]}...'"
                    item_progress = (j + 1) / len(line_items)
                    total_progress = (i + 0.1 + 0.8 * item_progress) / len(uploaded_files)
                    progress_bar.progress(total_progress, text=progress_text)

                    # --- Logique d'analyse experte en cascade ---
                    analysis = None
                    source = "Non déterminé"

                    # Étape 1: L'IA extrait les infos structurées (mots-clés, unité) de la description.
                    structured_info = get_structured_info_from_llm(description)

                    if structured_info:
                        keywords = structured_info.get("keywords")
                        invoice_unit = structured_info.get("unit", "unité")
                        
                        # Étape 2: On cherche la meilleure correspondance textuelle dans l'ADEME.
                        best_ademe_match = search_ademe_base_carbone(keywords, ademe_df)
                        
                        if best_ademe_match is not None:
                            ademe_unit = best_ademe_match['Unité français']
                            
                            ### MODIFIÉ : Appel à la fonction de validation experte ###
                            # Étape 3: L'IA valide la compatibilité des unités pour ce produit spécifique.
                            if are_units_compatible(description, invoice_unit, ademe_unit):
                                source = "ADEME (Validé)"
                                analysis = {
                                    "category": best_ademe_match.get('Type Ligne', 'ADEME'),
                                    "estimated_factor_kgCO2e_per_unit": best_ademe_match['Total poste non décomposé'],
                                    "justification": f"Correspondance validée. Produit ADEME : '{best_ademe_match['Nom base français']}'. Unité : {ademe_unit}.",
                                    "confidence_score": 0.95
                                }

                    # Étape 4: Si aucune correspondance validée n'est trouvée, on passe à l'estimation complète par l'IA.
                    if analysis is None:
                        source = "IA (Estimation)"
                        analysis = get_carbon_analysis_from_llm(
                            description=description,
                            quantity=float(item.get('quantity', 1))
                        )

                    if analysis:
                        factor = analysis.get('estimated_factor_kgCO2e_per_unit', 0)
                        quantity = float(item.get('quantity', 1))
                        carbon_kg = quantity * factor
                        
                        all_results.append({
                            "invoice_date": invoice_date, "description": description, "quantity": quantity,
                            "carbon_kg": carbon_kg, "category": analysis.get('category', 'Non classé'),
                            "confidence": analysis.get('confidence_score', 0),
                            "justification": analysis.get('justification', 'N/A'), "source": source
                        })

            os.remove(pdf_path)
            progress_bar.progress((i + 1) / len(uploaded_files), text=f"Fichier {i+1}/{len(uploaded_files)} traité.")

        if all_results:
            new_df = pd.DataFrame(all_results)
            st.session_state.results_df = pd.concat([st.session_state.results_df, new_df]).drop_duplicates().reset_index(drop=True)
            st.success(f"Analyse terminée ! {len(all_results)} nouveaux éléments ont été ajoutés.")
        else:
            st.warning("Aucun résultat n'a pu être extrait des fichiers fournis.")
        progress_bar.empty()

# --- SECTION D'AFFICHAGE DES RÉSULTATS ---
if not st.session_state.results_df.empty:
    df = st.session_state.results_df.copy()
    
    df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce')
    df.dropna(subset=['invoice_date'], inplace=True)
    df['invoice_month'] = df['invoice_date'].dt.to_period('M').astype(str)

    st.header("📊 Visualisation des Données", divider='rainbow')

    total_carbon = df['carbon_kg'].sum()
    ademe_count = df[df['source'] == 'ADEME (Validé)'].shape[0]
    total_count = df.shape[0]
    
    col1, col2 = st.columns(2)
    col1.metric("Empreinte Carbone Totale (kgCO₂e)", f"{total_carbon:,.2f}")
    if total_count > 0:
        col2.metric("Correspondances ADEME Validées", f"{ademe_count} / {total_count} ({ademe_count/total_count:.1%})")

    tab1, tab2 = st.tabs(["📈 Évolution Mensuelle", "📦 Répartition par Catégorie"])
    
    with tab1:
        st.subheader("Évolution de l'Empreinte Carbone par Mois")
        monthly_carbon = df.groupby('invoice_month')['carbon_kg'].sum().reset_index().sort_values('invoice_month')
        fig_line = px.line(monthly_carbon, x='invoice_month', y='carbon_kg', markers=True, labels={'invoice_month': 'Mois', 'carbon_kg': 'Empreinte Carbone (kgCO₂e)'}, title="Empreinte Carbone Mensuelle Cumulée")
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        st.subheader("Distribution de l'Empreinte Carbone par Catégorie")
        fig_box = px.box(df.sort_values(by='category'), x='category', y='carbon_kg', color='category', labels={'category': 'Catégorie d\'Émission', 'carbon_kg': 'Empreinte Carbone (kgCO₂e)'}, title="Distribution des Émissions par Catégorie", points='all')
        st.plotly_chart(fig_box, use_container_width=True)

    with st.expander("📄 Voir les données détaillées"):
        st.dataframe(df[['invoice_date', 'description', 'quantity', 'carbon_kg', 'category', 'confidence', 'source', 'justification']])

    if st.button("🧹 Réinitialiser les résultats", use_container_width=True):
        st.session_state.results_df = pd.DataFrame()
        st.rerun()

else:
    st.info("👋 Bienvenue ! Uploadez des factures et lancez l'analyse pour voir les résultats ici.")