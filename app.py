import streamlit as st
import pandas as pd
import sqlalchemy as sa
import plotly.express as px

# --- configuration de la page ---
# doit être la première commande streamlit
st.set_page_config(
    page_title="Premier League Dashboard",
    page_icon="⚽",
    layout="wide"
)

# --- connexion à la base de données (req 1) ---
# on cache la ressource pour ne pas recréer le moteur à chaque fois
@st.cache_resource
def get_db_engine():
    """crée et retourne un moteur sqlalchemy."""
    try:
        engine = sa.create_engine('postgresql:///premier_league')
        return engine
    except Exception as e:
        st.error(f"erreur de connexion à la base de données : {e}")
        return None

engine = get_db_engine()

# --- fonctions de récupération des données (req 2) ---
# on cache les données pour ne pas relancer la requête si les filtres ne changent pas
@st.cache_data
def load_all_team_names(_engine):
    """récupère tous les noms d'équipes pour le filtre."""
    if _engine is None:
        return pd.DataFrame(columns=['nomequipe']) # retourne un df vide en cas d'erreur
        
    query = "SELECT DISTINCT nomequipe FROM equipe ORDER BY nomequipe;"
    try:
        df = pd.read_sql(query, _engine)
        return df['nomequipe'].tolist() # retourne une liste de noms
    except Exception as e:
        st.warning(f"impossible de charger les noms d'équipes: {e}")
        return []

@st.cache_data
def load_team_player_stats(_engine, team_name):
    """récupère les statistiques des joueurs pour une équipe donnée."""
    if _engine is None:
        return pd.DataFrame()
        
    query = sa.text("""
        SELECT 
            j.nomjoueur, 
            s.buts, 
            s.passesdecisives, 
            s.cartonsjaunes, 
            s.cartonsrouges, 
            s.nbmatchesplayed
        FROM joueur j
        JOIN equipe e ON j.id_equipe = e.idequipe
        JOIN statistiquejoueur s ON j.idjoueur = s.idjoueur
        WHERE e.nomequipe = :team;
    """)
    try:
        df = pd.read_sql(query, _engine, params={"team": team_name})
        return df
    except Exception as e:
        st.warning(f"impossible de charger les stats des joueurs: {e}")
        return pd.DataFrame()

@st.cache_data
def load_team_results(_engine, team_name):
    """récupère le décompte des victoires/nuls/défaites pour une équipe."""
    if _engine is None:
        return pd.DataFrame()
        
    query = sa.text("""
        SELECT 
            resultat, 
            COUNT(resultat) AS total
        FROM resultatmatch r
        JOIN equipe e ON r.idequipe = e.idequipe
        WHERE e.nomequipe = :team
        GROUP BY resultat;
    """)
    try:
        df = pd.read_sql(query, _engine, params={"team": team_name})
        return df
    except Exception as e:
        st.warning(f"impossible de charger les résultats de l'équipe: {e}")
        return pd.DataFrame()


# --- fonctions de visualisation (req 3) ---
def plot_player_contributions(df):
    """crée un graphique à barres des buts et passes décisives."""
    if df.empty:
        return st.info("aucune donnée de joueur à afficher.")
    
    # préparer les données pour plotly
    df_plot = df[['nomjoueur', 'buts', 'passesdecisives']]
    df_melted = df_plot.melt('nomjoueur', var_name='Statistique', value_name='Total')
    
    fig = px.bar(
        df_melted, 
        x='nomjoueur', 
        y='Total', 
        color='Statistique', 
        barmode='group',
        title="Contributions des Joueurs (Buts et Passes)"
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_team_results_pie(df):
    """crée un graphique circulaire des résultats de l'équipe."""
    if df.empty:
        return st.info("aucun résultat de match à afficher.")
        
    fig = px.pie(
        df, 
        names='resultat', 
        values='total', 
        title="Répartition des Résultats des Matchs",
        color='resultat',
        color_discrete_map={'Victoire':'green', 'Nul':'orange', 'Défaite':'red'}
    )
    st.plotly_chart(fig, use_container_width=True)

# --- fonction utilitaire pour le téléchargement ---
@st.cache_data
def convert_df_to_csv(df):
    """convertit un dataframe en csv pour le téléchargement."""
    return df.to_csv(index=False, encoding='utf-8')


# =============================================================================
# --- interface utilisateur (dashboard) ---
# =============================================================================

st.title("⚽ Dashboard Premier League")

if engine is None:
    st.stop()

# --- barre latérale (filtres) ---
st.sidebar.header("Filtres")
team_list = load_all_team_names(engine)

if not team_list:
    st.error("aucune équipe n'a été trouvée dans la base de données. l'application ne peut pas continuer.")
    st.stop()

selected_team = st.sidebar.selectbox(
    "sélectionnez une équipe",
    options=team_list,
    index=team_list.index("Arsenal") # mettre une valeur par défaut
)

# --- chargement des données filtrées ---
player_df = load_team_player_stats(engine, selected_team)
results_df = load_team_results(engine, selected_team)

# --- affichage du dashboard ---
st.header(f"Analyse de l'équipe : {selected_team}")

# graphiques dynamiques (req 4)
col1, col2 = st.columns(2)
with col1:
    plot_player_contributions(player_df)
with col2:
    plot_team_results_pie(results_df)

# tableau interactif (req 5)
st.subheader("Données détaillées des joueurs")
st.dataframe(player_df, use_container_width=True)

# bouton de téléchargement (req 6)
csv_data = convert_df_to_csv(player_df)
st.download_button(
    label="📥 Télécharger les données en CSV",
    data=csv_data,
    file_name=f"stats_{selected_team.lower().replace(' ', '_')}.csv",
    mime='text/csv',
)