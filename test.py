import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(
    page_title="Tableau de Bord d'Analyse Carbone",
    page_icon="logo.png",
    layout="wide"
)

# --- INJECTION DU CSS PERSONNALISÉ ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("assets/style.css")


# --- DONNÉES DE DÉMONSTRATION ---
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
        'carbon_kg': [150, 125, 3500, 100, 250, 750, 150, 100, 75, 450],
        'category': [
            'Services Numériques', 'Déplacements Professionnels', 'Achats Informatiques',
            'Restauration & Fournitures', 'Déplacements Professionnels', 'Événementiel',
            'Services Numériques', 'Restauration & Fournitures', 'Services Numériques', 'Autres Services'
        ], 'source': ['IA (Estimation)', 'ADEME (Validé)', 'IA (Estimation)', 'IA (Estimation)',
                     'ADEME (Validé)', 'IA (Estimation)', 'ADEME (Validé)', 'ADEME (Validé)',
                     'IA (Estimation)', 'IA (Estimation)'],
        'confidence': [0.85, 0.95, 0.90, 0.80, 0.95, 0.88, 0.95, 0.95, 0.82, 0.78]
    }
    df = pd.DataFrame(data)
    df['invoice_date'] = pd.to_datetime(df['invoice_date'])
    return df

if 'results_df' not in st.session_state:
    st.session_state.results_df = get_demo_data()

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.header("Configuration de l'API")
    st.subheader("API Gemini")
    st.info("Nécessaire pour analyser vos factures PDF.")
    st.text_input("Entrez votre clé API Gemini", type="password", value="fake-gemini-api-key-for-demo")

# --- INTERFACE PRINCIPALE ---

# --- EN-TÊTE ---
col1, col2 = st.columns([0.08, 0.92])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.title("Tableau de Bord d'Analyse Carbone")
    st.subheader("Analysez l'empreinte carbone de vos dépenses grâce à l'IA.")

st.markdown("---")

# --- SECTION DES ACTIONS ---
col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Chargez vos factures")
    st.file_uploader(
        "Déposez vos fichiers PDF ici",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    st.button("Lancer l'analyse des PDF", use_container_width=True, disabled=True)

with col2:
    st.subheader("Inviter vos collaborateurs")
    with st.form("invitation_form"):
        st.text_area(
            "Adresses e-mail",
            placeholder="Entrez les adresses e-mail de vos employés, une par ligne...",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("Envoyer les invitations", use_container_width=True)
        if submitted:
            # Ici, vous mettriez la logique pour envoyer les e-mails
            st.success("Invitations envoyées avec succès !")

# --- ENTRÉE MANUELLE (DANS UN EXPANDER) ---
with st.expander("Ajouter une entrée manuelle"):
    with st.form("manual_entry_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.date_input("Date", value=datetime.date(2025, 11, 4))
        with c2:
            st.text_input("Description du produit ou service")
        with c3:
            st.number_input("Quantité", min_value=0.0, value=1.0, step=0.1)
        st.form_submit_button("Ajouter l'entrée", disabled=True, use_container_width=True)


# --- SECTION D'AFFICHAGE DES RÉSULTATS ---
if not st.session_state.results_df.empty:
    df = st.session_state.results_df.copy()
    df['invoice_month'] = df['invoice_date'].dt.to_period('M').astype(str)

    st.header("Visualisation des Données", divider='green')

    # --- Métriques Clés ---
    total_carbon = df['carbon_kg'].sum()
    ademe_count = df[df['source'] == 'ADEME (Validé)'].shape[0]
    total_count = df.shape[0]

    m1, m2 = st.columns(2)
    m1.metric("Empreinte Carbone Totale (kgCO₂e)", f"{total_carbon:,.0f}")
    if total_count > 0:
        m2.metric("Correspondances ADEME Validées", f"{ademe_count} / {total_count} ({ademe_count/total_count:.0%})")

    # --- Onglets avec les Graphiques ---
    tab1, tab2 = st.tabs(["Évolution Mensuelle", "Répartition par Catégorie"])
    
    with tab1:
        st.subheader("Évolution de l'Empreinte Carbone Globale par Mois")
        monthly_carbon_total = df.groupby('invoice_month')['carbon_kg'].sum().reset_index().sort_values('invoice_month')
        fig_line = px.line(
            monthly_carbon_total, x='invoice_month', y='carbon_kg', markers=True,
            labels={'invoice_month': 'Mois', 'carbon_kg': 'Empreinte Carbone (kgCO₂e)'}
        )
        fig_line.update_traces(line=dict(width=4, color='#00796b'))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        category_carbon = df.groupby('category')['carbon_kg'].sum().reset_index()
        st.subheader("Répartition des Émissions par Catégorie")
        fig_pie = px.pie(
            category_carbon, names='category', values='carbon_kg', hole=0.4,
            color_discrete_sequence=px.colors.sequential.Greens_r
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        # --- LA LIGNE CORRIGÉE EST ICI ---
        st.plotly_chart(fig_pie, use_container_width=True)
        # ----------------------------------

        st.markdown("---")

        st.subheader("Comparaison des Émissions par Catégorie")
        fig_bar = px.bar(
            category_carbon.sort_values(by='carbon_kg', ascending=False), x='category', y='carbon_kg',
            color='category', labels={'category': 'Catégorie d\'Émission', 'carbon_kg': 'Total Empreinte Carbone (kgCO₂e)'},
            color_discrete_sequence=px.colors.sequential.Greens_r
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("Voir les données détaillées de la démonstration"):
        st.dataframe(df[['invoice_date', 'description', 'quantity', 'carbon_kg', 'category', 'source', 'confidence']])