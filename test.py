import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import time
import numpy as np

# --- CONFIGURATION DE LA PAGE STREAMLIT ---
st.set_page_config(
    page_title="Tableau de Bord d'Analyse Carbone",
    page_icon="logo.png",  # Assurez-vous d'avoir un fichier logo.png
    layout="wide"
)

# --- INJECTION DU CSS PERSONNALISÉ ---
# Assurez-vous d'avoir un fichier assets/style.css ou commentez cette section
try:
    def local_css(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    local_css("assets/style.css")
except FileNotFoundError:
    st.warning("Le fichier 'assets/style.css' est introuvable. Le style par défaut sera utilisé.")


# --- DONNÉES DE DÉMONSTRATION SUR 8 MOIS ---
def get_demo_data():
    """Crée un DataFrame pandas avec des données fictives cohérentes sur 8 mois."""
    dates = pd.to_datetime(pd.date_range(start="2025-01-01", end="2025-08-31", freq='D'))
    data = []
    categories_options = [
        'Services Numériques', 'Déplacements Professionnels', 'Achats Informatiques',
        'Restauration & Fournitures', 'Événementiel', 'Autres Services'
    ]
    descriptions = {
        'Services Numériques': ['Abonnement Logiciel CRM', 'Service Cloud (Mensuel)', 'Licence suite créative (annuel)', 'Hébergement Web'],
        'Déplacements Professionnels': ['Billet de train Paris-Lyon A/R', '2 Nuits d\'hôtel pour conférence', 'Vol A/R New York', 'Location de voiture'],
        'Achats Informatiques': ['Achat de 10 ordinateurs portables', 'Écrans 4K pour graphistes', 'Serveur de stockage', 'Accessoires (claviers, souris)'],
        'Restauration & Fournitures': ['Prestation traiteur événement', 'Fournitures de bureau écologiques', 'Abonnement café', 'Commande de papier recyclé'],
        'Événementiel': ['Location stand salon ProTech', 'Impression de brochures', 'Service de sécurité événement', 'Location matériel audiovisuel'],
        'Autres Services': ['Conseil en stratégie marketing', 'Formation équipe', 'Service de nettoyage', 'Honoraires juridiques']
    }

    for _ in range(100): # Générer 100 factures aléatoires
        date = np.random.choice(dates)
        category = np.random.choice(categories_options)
        description = np.random.choice(descriptions[category])
        quantity = np.random.randint(1, 15)
        carbon_kg = abs(np.random.normal(loc=300, scale=400)) + (200 if category == 'Achats Informatiques' else 0)
        source = np.random.choice(['IA (Estimation)', 'ADEME (Validé)'], p=[0.6, 0.4])
        confidence = np.random.uniform(0.75, 0.98) if source == 'ADEME (Validé)' else np.random.uniform(0.70, 0.90)

        data.append({
            'invoice_date': date,
            'description': description,
            'quantity': quantity,
            'carbon_kg': round(carbon_kg, 2),
            'category': category,
            'source': source,
            'confidence': round(confidence, 2)
        })

    df = pd.DataFrame(data)
    df['invoice_date'] = pd.to_datetime(df['invoice_date'])
    return df.sort_values(by='invoice_date').reset_index(drop=True)


# Initialise les données de démo dans l'état de la session si elles n'existent pas
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
    # Assurez-vous d'avoir un fichier logo.png ou remplacez par une autre image
    try:
        st.image("logo.png", width=80)
    except:
        st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=80)
with col2:
    st.title("Tableau de Bord d'Analyse Carbone")
    st.subheader("Analysez l'empreinte carbone de vos dépenses grâce à l'IA.")

st.markdown("---")

# --- SECTION DES ACTIONS (SIMULATION) ---
col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Chargez vos factures")
    uploaded_files = st.file_uploader(
        "Déposez vos fausses factures PDF ici pour la démo",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # Le bouton est désactivé s'il n'y a pas de fichier
    analyze_button = st.button("Lancer l'analyse des PDF", use_container_width=True, disabled=not uploaded_files)

    if analyze_button:
        # Simulation d'une analyse qui prend du temps
        progress_bar = st.progress(0, text="Analyse en cours... Veuillez patienter.")
        for percent_complete in range(100):
            time.sleep(0.03)
            progress_bar.progress(percent_complete + 1, text=f"Analyse en cours... {percent_complete+1}%")
        time.sleep(0.5)
        progress_bar.empty() # Fait disparaître la barre
        st.success(f"{len(uploaded_files)} facture(s) analysée(s) avec succès ! Le tableau de bord est à jour.")


with col2:
    st.subheader("Inviter vos collaborateurs")
    with st.form("invitation_form"):
        st.text_area(
            "Adresses e-mail",
            placeholder="Entrez une ou plusieurs fausses adresses e-mail pour la démo...",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("Envoyer les invitations", use_container_width=True)
        if submitted:
            # Simulation d'envoi réussi
            st.success("Invitations envoyées avec succès !")

# --- ENTRÉE MANUELLE (DANS UN EXPANDER) ---
# --- ENTRÉE MANUELLE (DANS UN EXPANDER) ---
with st.expander("Ajouter une entrée manuelle"):
    # On utilise un formulaire pour regrouper les champs et le bouton
    # clear_on_submit=True videra les champs après l'ajout
    with st.form("manual_entry_form", clear_on_submit=True):
        
        # Obtenir la liste unique des catégories existantes pour le sélecteur
        categories_list = st.session_state.results_df['category'].unique()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            manual_date = st.date_input("Date", value=datetime.date.today())
        with c2:
            manual_desc = st.text_input("Description", placeholder="Ex: Billet de train")
        with c3:
            manual_qty = st.number_input("Quantité", min_value=1, value=1, step=1)
        with c4:
            manual_cat = st.selectbox("Catégorie", options=categories_list)

        # Bouton de soumission du formulaire
        submitted = st.form_submit_button("Ajouter l'entrée", use_container_width=True)

        # Logique à exécuter si le bouton est cliqué
        if submitted:
            # Petite validation pour s'assurer que la description n'est pas vide
            if manual_desc:
                # Création d'une nouvelle ligne de données sous forme de dictionnaire
                new_entry = {
                    'invoice_date': pd.to_datetime(manual_date),
                    'description': manual_desc,
                    'quantity': manual_qty,
                    # Pour la démo, on assigne une valeur carbone simple et arbitraire
                    'carbon_kg': 75 * manual_qty,
                    'category': manual_cat,
                    'source': 'Entrée Manuelle',
                    'confidence': 1.0  # Confiance de 100% car c'est manuel
                }
                
                # Conversion du dictionnaire en DataFrame
                new_df = pd.DataFrame([new_entry])
                
                # Ajout de la nouvelle ligne au DataFrame principal stocké dans la session
                st.session_state.results_df = pd.concat([st.session_state.results_df, new_df], ignore_index=True)
                
                st.success("Entrée ajoutée avec succès !")
            else:
                st.warning("Veuillez entrer une description pour l'entrée.")

# --- SECTION D'AFFICHAGE DES RÉSULTATS ---
df = st.session_state.results_df.copy()
df['invoice_month'] = df['invoice_date'].dt.strftime('%Y-%m')

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
    st.plotly_chart(fig_pie, use_container_width=True)

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