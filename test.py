import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(
    page_title="Tableau de Bord d'Analyse Carbone",
    page_icon="logo.png",  # Utilise votre logo comme icône d'onglet
    layout="wide"
)

# --- DONNÉES DE DÉMONSTRATION (POUR LA VITRINE) ---
def get_demo_data():
    """Crée un DataFrame pandas avec des données fictives cohérentes."""
    data = {
        'invoice_date': [
            '2025-01-15', '2025-01-20', '2025-02-05', '2025-02-10', 
            '2025-02-18', '2025-03-02', '2025-03-12', '2025-03-25',
            '2025-01-22', '2025-03-15'
        ],
        'description': [
            'Abonnement Logiciel CRM', 'Billet de train Paris-Lyon A/R', 
            'Achat de 10 ordinateurs portables', 'Prestation traiteur événement',
            '2 Nuits d\'hôtel pour conférence', 'Location stand salon ProTech', 
            'Licence suite créative (annuel)', 'Fournitures de bureau écologiques',
            'Service Cloud (Janvier)', 'Conseil en stratégie marketing'
        ],
        'quantity': [1, 1, 10, 1, 2, 1, 1, 15, 1, 1],
        'carbon_kg': [
            150, 125, 3500, 100, 250, 750, 150, 100, 75, 450
        ],
        'category': [
            'Services Numériques', 'Déplacements Professionnels', 
            'Achats Informatiques', 'Restauration & Fournitures',
            'Déplacements Professionnels', 'Événementiel',
            'Services Numériques', 'Restauration & Fournitures',
            'Services Numériques', 'Autres Services'
        ],
        'source': [
            'IA (Estimation)', 'ADEME (Validé)', 'IA (Estimation)', 
            'IA (Estimation)', 'ADEME (Validé)', 'IA (Estimation)',
            'ADEME (Validé)', 'ADEME (Validé)', 'IA (Estimation)', 
            'IA (Estimation)'
        ],
        'confidence': [0.85, 0.95, 0.90, 0.80, 0.95, 0.88, 0.95, 0.95, 0.82, 0.78]
    }
    df = pd.DataFrame(data)
    df['invoice_date'] = pd.to_datetime(df['invoice_date'])
    return df

# Initialise l'état de la session avec les données de démo
if 'results_df' not in st.session_state:
    st.session_state.results_df = get_demo_data()

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.header("🔑 Configuration de l'API")

    st.subheader("API Gemini")
    st.info("""
    **Nécessaire pour analyser vos factures PDF.**
    """)
    st.text_input("Entrez votre clé API Gemini", type="password", value="fake-gemini-api-key-for-demo")

# --- INTERFACE PRINCIPALE ---

# --- EN-TÊTE AVEC LOGO ET TITRE ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    # Assurez-vous que le fichier 'logo.png' se trouve dans le même dossier que votre script.
    st.image("logo.png", width=100)
with col2:
    st.title("Tableau de Bord d'Analyse Carbone")
    st.subheader("Analysez l'empreinte carbone de vos dépenses grâce à l'IA.")

# --- ZONES DE CHARGEMENT ---
st.markdown("---")
st.write("Chargez une ou plusieurs factures PDF")
st.file_uploader(
    "Drag and drop files here",
    type="pdf",
    accept_multiple_files=True,
    label_visibility="collapsed"
)
st.button("🚀 Lancer l'analyse des PDF", use_container_width=True, disabled=True)

# --- SECTION D'ENTRÉE MANUELLE ---
with st.expander("✍️ Ajouter une entrée manuelle"):
    with st.form("manual_entry_form"):
        st.date_input("Date", value=datetime.date(2025, 11, 4))
        st.text_input("Description du produit ou service")
        st.number_input("Quantité", min_value=0.0, value=1.0, step=0.1)
        st.form_submit_button("Ajouter l'entrée", disabled=True)

# --- SECTION D'AFFICHAGE DES RÉSULTATS (VITRINE) ---
if not st.session_state.results_df.empty:
    df = st.session_state.results_df.copy()
    
    df['invoice_month'] = df['invoice_date'].dt.to_period('M').astype(str)

    st.header("📊 Visualisation des Données", divider='rainbow')

    # --- Métriques Clés ---
    total_carbon = df['carbon_kg'].sum()
    ademe_count = df[df['source'] == 'ADEME (Validé)'].shape[0]
    total_count = df.shape[0]
    
    col1, col2 = st.columns(2)
    col1.metric("Empreinte Carbone Totale (kgCO₂e)", f"{total_carbon:,.0f}")
    if total_count > 0:
        col2.metric("Correspondances ADEME Validées", f"{ademe_count} / {total_count} ({ademe_count/total_count:.0%})")

    # --- Onglets avec les Graphiques ---
    tab1, tab2 = st.tabs(["📈 Évolution Mensuelle", "📦 Répartition par Catégorie"])
    
    with tab1:
        st.subheader("Évolution de l'Empreinte Carbone Globale par Mois")
        # NOUVEAU: Regroupe toutes les catégories pour obtenir une seule courbe
        monthly_carbon_total = df.groupby('invoice_month')['carbon_kg'].sum().reset_index().sort_values('invoice_month')
        
        # NOUVEAU: Utilise un graphique en ligne simple (px.line)
        fig_line = px.line(
            monthly_carbon_total, 
            x='invoice_month', 
            y='carbon_kg', 
            markers=True, # Ajoute des points sur la courbe pour chaque mois
            labels={'invoice_month': 'Mois', 'carbon_kg': 'Empreinte Carbone (kgCO₂e)'}, 
            title="Empreinte Carbone Mensuelle Cumulée"
        )
        fig_line.update_traces(line=dict(width=4)) # Épaissit la ligne pour une meilleure visibilité
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        category_carbon = df.groupby('category')['carbon_kg'].sum().reset_index()
        
        st.subheader("Répartition des Émissions par Catégorie")
        fig_pie = px.pie(
            category_carbon, 
            names='category', 
            values='carbon_kg', 
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---") # Ajoute un séparateur visuel

        # NOUVEAU: Ajout du graphique en barres
        st.subheader("Comparaison des Émissions par Catégorie")
        fig_bar = px.bar(
            category_carbon.sort_values(by='carbon_kg', ascending=False), # Trie pour une meilleure lisibilité
            x='category',
            y='carbon_kg',
            color='category', # Une couleur par catégorie
            labels={'category': 'Catégorie d\'Émission', 'carbon_kg': 'Total Empreinte Carbone (kgCO₂e)'},
            title="Total des Émissions par Catégorie"
        )
        st.plotly_chart(fig_bar, use_container_width=True)


    with st.expander("📄 Voir les données détaillées de la démonstration"):
        st.dataframe(df[['invoice_date', 'description', 'quantity', 'carbon_kg', 'category', 'source', 'confidence']])