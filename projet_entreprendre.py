import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any


# CONFIGURATION DE LA PAGE STREAMLIT
st.set_page_config(
    page_title="Analyse Carbone par IA",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Tableau de Bord d'Analyse Carbone par IA")
st.markdown("Uploadez vos factures PDF pour analyser et visualiser leur empreinte carbone.")


# CONFIGURATION DE L'API GEMINI (DANS LA SIDEBAR), on peut le changer plus tard 
with st.sidebar:
    st.header("🔑 Configuration de l'API")
    st.markdown("Pour utiliser cette application, veuillez fournir votre clé API Google Gemini.")
    
    # Utilise st.secrets pour le déploiement, sinon un champ de saisie
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

# Utilisation du cache pour éviter de refaire les mêmes appels API coûteux
@st.cache_data
def extract_invoice_data_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """Extrait les données structurées d'un PDF en utilisant l'API Gemini."""
    model = genai.GenerativeModel('gemini-2.5-pro') # Utilisation du modèle correct
    
    # On doit uploader le fichier pour que Gemini puisse le lire
    invoice_file = genai.upload_file(path=pdf_path, display_name=Path(pdf_path).name)

    # Prompt amélioré pour inclure la date de la facture
    prompt = """
    Tu es un système expert d'extraction de données de factures.
    Analyse le document fourni et extrais les informations suivantes : le numéro de facture,
    le nom du vendeur, la date de la facture (au format YYYY-MM-DD), et la liste complète 
    des articles facturés ('line_items').
    Pour chaque article, je veux la description, la quantité et le prix total.
    Ton unique et seule réponse doit être un objet JSON valide, sans aucun texte avant ou après.
    Le format doit être exactement :
    {
      "invoice_number": "string",
      "seller_name": "string",
      "invoice_date": "YYYY-MM-DD",
      "line_items": [
        {
          "description": "string",
          "quantity": "float",
          "total_price": "float"
        }
      ]
    }
    """
    
    try:
        response = model.generate_content([prompt, invoice_file])
        # Nettoyage pour extraire le JSON même s'il est dans un bloc de code
        json_text_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
        cleaned_text = json_text_match.group(1) if json_text_match else response.text
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des données du PDF : {e}")
        return None
    finally:
        # Supprime le fichier du service après traitement
        genai.delete_file(invoice_file.name)

@st.cache_data
def get_carbon_analysis_from_llm(description: str, quantity: float) -> Dict[str, Any]:
    """Analyse un article de facture pour estimer son empreinte carbone."""
    model = genai.GenerativeModel('gemini-2.5-pro') 

    prompt = f"""
    Tu es un expert en analyse du cycle de vie et en calcul d'empreinte carbone.
    Ta mission est d'analyser la ligne de facture suivante et de fournir une estimation de son facteur d'émission en kgCO2e.
    Description de l'article : "{description}"
    Quantité : {quantity}
    Analyse la description pour comprendre la nature du service ou du produit.
    Décompose-le en ses sources d'émission probables (ex: consommation électrique, matériaux, transport, déchets).
    Sur la base de cette décomposition, estime un facteur d'émission réaliste en kgCO2e par unité de l'article.
    Fournis une justification claire et concise pour ton calcul.
    Réponds UNIQUEMENT au format JSON suivant :
    {{
      "category": "La catégorie d'émission la plus pertinente (ex: 'Services événementiels', 'Matériel informatique', 'Consommables', 'Transport', 'Logiciels')",
      "estimated_factor_kgCO2e_per_unit": <nombre flottant>,
      "justification": "Explication détaillée de comment tu es arrivé à ce facteur, en mentionnant tes hypothèses.",
      "confidence_score": <nombre flottant entre 0.0 et 1.0>
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        json_text_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
        cleaned_text = json_text_match.group(1) if json_text_match else response.text
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Erreur pendant l'analyse carbone pour '{description[:30]}...' : {e}")
        return None


# LOGIQUE PRINCIPALE DE L'APPLICATION
# Initialisation du session_state pour stocker les résultats
if 'results_df' not in st.session_state:
    st.session_state.results_df = pd.DataFrame()

# Zone d'upload
uploaded_files = st.file_uploader(
    "Chargez une ou plusieurs factures au format PDF",
    type="pdf",
    accept_multiple_files=True
)

if st.button("🚀 Lancer l'analyse", disabled=(not uploaded_files or not api_key), use_container_width=True):
    # Crée un dossier temporaire pour stocker les PDF uploadés
    with st.spinner("Analyse en cours... Cette opération peut prendre quelques minutes."):
        temp_dir = Path("./temp_pdfs")
        temp_dir.mkdir(exist_ok=True)
        
        all_results = []

        # Barre de progression globale
        progress_bar = st.progress(0, text="Initialisation...")
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Enregistrer le fichier temporairement
            pdf_path = temp_dir / uploaded_file.name
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # ÉTAPE 1: Extraction des données du PDF
            progress_text = f"Fichier {i+1}/{len(uploaded_files)} : Extraction des données de '{uploaded_file.name}'..."
            progress_bar.progress((i + 0.1) / len(uploaded_files), text=progress_text)
            
            extracted_data = extract_invoice_data_from_pdf(str(pdf_path))
            
            if extracted_data and "line_items" in extracted_data:
                invoice_date = extracted_data.get("invoice_date", None)
                line_items = extracted_data["line_items"]

                # ÉTAPE 2: Analyse carbone pour chaque article
                for j, item in enumerate(line_items):
                    progress_text = f"Fichier {i+1}/{len(uploaded_files)} : Analyse de '{item.get('description', 'N/A')[:30]}...'"
                    # Calculer la progression à l'intérieur de la boucle des items
                    item_progress = (j + 1) / len(line_items)
                    total_progress = (i + 0.1 + 0.8 * item_progress) / len(uploaded_files) # 80% du temps est pour cette étape
                    progress_bar.progress(total_progress, text=progress_text)

                    analysis = get_carbon_analysis_from_llm(
                        description=item.get('description', 'N/A'),
                        quantity=float(item.get('quantity', 1))
                    )
                    
                    if analysis:
                        factor = analysis.get('estimated_factor_kgCO2e_per_unit', 0)
                        quantity = float(item.get('quantity', 1))
                        carbon_kg = quantity * factor
                        
                        result_item = {
                            "invoice_date": invoice_date,
                            "description": item.get('description'),
                            "quantity": quantity,
                            "carbon_kg": carbon_kg,
                            "category": analysis.get('category', 'Non classé'),
                            "confidence": analysis.get('confidence_score', 0),
                            "justification": analysis.get('justification', 'N/A')
                        }
                        all_results.append(result_item)

            # Supprimer le fichier temporaire
            os.remove(pdf_path)
            progress_bar.progress((i + 1) / len(uploaded_files), text=f"Fichier {i+1}/{len(uploaded_files)} traité.")

        if all_results:
            new_df = pd.DataFrame(all_results)
            # Concaténer avec les anciens résultats s'il y en a
            st.session_state.results_df = pd.concat([st.session_state.results_df, new_df]).drop_duplicates().reset_index(drop=True)
            st.success(f"Analyse terminée ! {len(all_results)} nouveaux éléments ont été ajoutés.")
        else:
            st.warning("Aucun résultat n'a pu être extrait des fichiers fournis.")

        progress_bar.empty()



# SECTION D'AFFICHAGE DES RÉSULTATS
if not st.session_state.results_df.empty:
    df = st.session_state.results_df.copy()
    
    # Préparation des données pour les graphiques
    df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce')
    df.dropna(subset=['invoice_date'], inplace=True) # Ignorer les lignes sans date valide
    df['invoice_month'] = df['invoice_date'].dt.to_period('M').astype(str)

    st.header("📊 Visualisation des Données", divider='rainbow')

    # Métriques clés
    total_carbon = df['carbon_kg'].sum()
    unique_categories = df['category'].nunique()
    
    col1, col2 = st.columns(2)
    col1.metric("Empreinte Carbone Totale (kgCO₂e)", f"{total_carbon:,.2f}")
    col2.metric("Nombre de Catégories d'Émissions", f"{unique_categories}")

    # --- Graphiques ---
    tab1, tab2 = st.tabs(["📈 Évolution Mensuelle", "📦 Répartition par Catégorie"])

    with tab1:
        st.subheader("Évolution de l'Empreinte Carbone par Mois")
        monthly_carbon = df.groupby('invoice_month')['carbon_kg'].sum().reset_index()
        monthly_carbon = monthly_carbon.sort_values('invoice_month')
        
        fig_line = px.line(
            monthly_carbon, 
            x='invoice_month', 
            y='carbon_kg', 
            markers=True,
            labels={'invoice_month': 'Mois', 'carbon_kg': 'Empreinte Carbone (kgCO₂e)'},
            title="Empreinte Carbone Mensuelle Cumulée"
        )
        fig_line.update_traces(line_color='#0A6847', marker=dict(color='#7ABA78', size=8))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        st.subheader("Distribution de l'Empreinte Carbone par Catégorie")
        
        fig_box = px.box(
            df.sort_values(by='category'), 
            x='category', 
            y='carbon_kg',
            color='category',
            labels={'category': 'Catégorie d\'Émission', 'carbon_kg': 'Empreinte Carbone (kgCO₂e)'},
            title="Distribution des Émissions par Catégorie",
            points='all' # Affiche tous les points de données
        )
        st.plotly_chart(fig_box, use_container_width=True)

    # --- Tableau de données ---
    with st.expander("📄 Voir les données détaillées"):
        st.dataframe(df)

    # --- Bouton de réinitialisation ---
    if st.button("🧹 Réinitialiser les résultats", use_container_width=True):
        st.session_state.results_df = pd.DataFrame()
        st.rerun()

else:
    st.info("👋 Bienvenue ! Uploadez des factures et lancez l'analyse pour voir les résultats ici.")