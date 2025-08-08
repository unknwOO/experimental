import streamlit as st
import anthropic
import json
import uuid
import os
import time
import random
import pyperclip
from datetime import datetime, timedelta

CONVERSATION_TIME = 7 * 24 * 60 * 60

# Configuration de la page
st.set_page_config(
    page_title="Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

class AuthManager:
    def __init__(self):
        self.users_file = "users.json"
        self.admin_username = st.secrets.get("ADMIN_USERNAME")
        self.admin_password = st.secrets.get("ADMIN_PASSWORD")
        
        # Initialiser le fichier utilisateurs s'il n'existe pas
        if not os.path.exists(self.users_file):
            initial_data = {
                "global_password": "skool-empire-25",
                "users": {}
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
    
    def _load_users(self):
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"global_password": "skool-empire-25", "users": {}}
    
    def _save_users(self, data):
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            raise e
    
    def authenticate_admin(self, username, password):
        return username == self.admin_username and password == self.admin_password
    
    def authenticate_user(self, username, password):
        data = self._load_users()
        return username in data["users"] and password == data["global_password"]
    
    def get_user_credits(self, username):
        data = self._load_users()
        return data["users"].get(username, {}).get("credits", 0)
    
    def update_user_credits(self, username, new_credits):
        data = self._load_users()
        if username in data["users"]:
            data["users"][username]["credits"] = new_credits
            self._save_users(data)
            return True
        return False
    
    def deduct_credits(self, username, amount):
        data = self._load_users()
        if username in data["users"]:
            current_credits = data["users"][username]["credits"]
            if current_credits >= amount:
                data["users"][username]["credits"] = current_credits - amount
                data["users"][username]["last_activity"] = datetime.now().isoformat()
                self._save_users(data)
                return True
        return False
    
    def add_user(self, username, credits=30):
        data = self._load_users()
        if username not in data["users"]:
            data["users"][username] = {
                "credits": credits,
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "last_activity": None,
                "total_scripts": 0,
                "total_hooks": 0
            }
            self._save_users(data)
            return True
        return False
    
    def remove_user(self, username):
        data = self._load_users()
        if username in data["users"]:
            del data["users"][username]
            self._save_users(data)
            
            try:
                with open("conversations.json", 'r', encoding='utf-8') as f:
                    conv_data = json.load(f)
                
                if username in conv_data:
                    del conv_data[username]
                
                with open("conversations.json", 'w', encoding='utf-8') as f:
                    json.dump(conv_data, f, ensure_ascii=False, indent=2)
            except:
                pass
            
            return True
        return False
    
    def update_global_password(self, new_password):
        data = self._load_users()
        data["global_password"] = new_password
        self._save_users(data)
    
    def get_all_users(self):
        data = self._load_users()
        return data["users"]
    
    def update_last_login(self, username):
        data = self._load_users()
        if username in data["users"]:
            data["users"][username]["last_login"] = datetime.now().isoformat()
            self._save_users(data)
    
    def increment_script_count(self, username):
        """Incrémente le compteur de scripts générés"""
        data = self._load_users()
        if username in data["users"]:
            if "total_scripts" not in data["users"][username]:
                data["users"][username]["total_scripts"] = 0
            data["users"][username]["total_scripts"] += 1
            self._save_users(data)
            return True
        return False
    
    def increment_hook_count(self, username):
        """Incrémente le compteur de hooks générés"""
        data = self._load_users()
        if username in data["users"]:
            if "total_hooks" not in data["users"][username]:
                data["users"][username]["total_hooks"] = 0
            data["users"][username]["total_hooks"] += 1
            self._save_users(data)
            return True
        return False
    
    def get_user_stats(self, username):
        """Récupère les statistiques d'un utilisateur"""
        data = self._load_users()
        if username in data["users"]:
            user_data = data["users"][username]
            return {
                "credits": user_data.get("credits", 0),
                "total_scripts": user_data.get("total_scripts", 0),
                "total_hooks": user_data.get("total_hooks", 0),
                "created_at": user_data.get("created_at"),
                "last_login": user_data.get("last_login")
            }
        return None

class ViralScriptGenerator:
    def __init__(self, username=None):
        self.username = username

        self.api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        self.db_file = "conversations.json"
        
        # Initialiser le fichier de base de données s'il n'existe pas
        if not os.path.exists(self.db_file):
            initial_data = {}
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
        
        # Charger les prompts depuis les secrets Streamlit
        self.script_prompt = st.secrets.get("SCRIPT_PROMPT", "")
        self.hook_prompt = st.secrets.get("HOOK_PROMPT", "")
        self.animals_list = st.secrets.get("ANIMALS_LIST", "")
    
    def _load_prompt(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            st.error(f"❌ Fichier non trouvé: {file_path}")
            return ""
    
    def _load_conversations(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_conversations(self, data):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            raise e
    
    def _cleanup_old_conversations(self, data):
        """Supprime les conversations de plus de 10 minutes"""
        current_time = datetime.now()
        cleaned_data = data.copy()
        
        for username in list(cleaned_data.keys()):
            if "conversations" in cleaned_data[username]:
                # Filtrer les conversations récentes
                recent_conversations = []
                for conv in cleaned_data[username]["conversations"]:
                    if "created_at" in conv:
                        try:
                            conv_time = datetime.fromisoformat(conv["created_at"])
                            # Garder seulement les conversations de moins de 24 heures
                            if (current_time - conv_time).total_seconds() < CONVERSATION_TIME:  # 24 heures = 86400 secondes
                                recent_conversations.append(conv)
                        except:
                            # Si erreur de parsing, garder la conversation
                            recent_conversations.append(conv)
                    else:
                        # Si pas de timestamp, supprimer (ancien format)
                        continue
                
                cleaned_data[username]["conversations"] = recent_conversations
        
        return cleaned_data
    
    def get_conversation_time_info(self, conversation):
        if "created_at" not in conversation:
            return None
        
        try:
            conv_time = datetime.fromisoformat(conversation["created_at"])
            current_time = datetime.now()
            elapsed_seconds = (current_time - conv_time).total_seconds()
            remaining_seconds = CONVERSATION_TIME - elapsed_seconds
            
            if remaining_seconds <= 0:
                return "Expiré"
            elif remaining_seconds < 60:
                return f"{int(remaining_seconds)}s restantes"
            elif remaining_seconds < 3600:  # Moins d'1 heure
                minutes = int(remaining_seconds // 60)
                seconds = int(remaining_seconds % 60)
                return f"{minutes}m {seconds}s restantes"
            elif remaining_seconds < 86400:  # Moins d'1 jour
                hours = int(remaining_seconds // 3600)
                minutes = int((remaining_seconds % 3600) // 60)
                return f"{hours}h {minutes}m restantes"
            else:  # Plus d'1 jour
                days = int(remaining_seconds // 86400)
                if days == 1:
                    return f"{days} jour restant"
                else:
                    return f"{days} jours restants"
        except:
            return None
    
    def force_cleanup(self):
        """Force le nettoyage des anciennes conversations"""
        data = self._load_conversations()
        cleaned_data = self._cleanup_old_conversations(data)
        self._save_conversations(cleaned_data)
        return cleaned_data
    
    def _get_or_create_conversation(self, animal):
        data = self._load_conversations()
        
        # Nettoyer les anciennes conversations
        data = self._cleanup_old_conversations(data)
        
        if self.username not in data:
            data[self.username] = {"conversations": []}
        
        for conv in data[self.username]["conversations"]:
            if conv["animal"].lower() == animal.lower():
                return conv
        
        new_conv = {
            "id": str(uuid.uuid4()),
            "animal": animal,
            "scripts": [],
            "hooks": [],
            "created_at": datetime.now().isoformat()
        }
        
        data[self.username]["conversations"].append(new_conv)
        self._save_conversations(data)
        return new_conv
    
    def add_script_to_conversation(self, animal, script_content):
        try:
            data = self._load_conversations()
            
            # Nettoyer les anciennes conversations
            data = self._cleanup_old_conversations(data)
            
            # Créer l'utilisateur s'il n'existe pas
            if self.username not in data:
                data[self.username] = {"conversations": []}
            
            # Chercher une conversation existante
            for conv in data[self.username]["conversations"]:
                if conv["animal"].lower() == animal.lower():
                    script_entry = {
                        "content": script_content,
                        "char_count": len(script_content)
                    }
                    conv["scripts"].append(script_entry)
                    self._save_conversations(data)
                    return True
            
            # Créer une nouvelle conversation
            new_conv = {
                "id": str(uuid.uuid4()),
                "animal": animal,
                "scripts": [{
                    "content": script_content,
                    "char_count": len(script_content)
                }],
                "hooks": [],
                "created_at": datetime.now().isoformat()
            }
            
            data[self.username]["conversations"].append(new_conv)
            self._save_conversations(data)
            return True
        
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False

    def add_hooks_to_conversation(self, conversation_id, hooks_content):
        data = self._load_conversations()
        
        # Nettoyer les anciennes conversations
        data = self._cleanup_old_conversations(data)
        
        if self.username in data:
            for conv in data[self.username]["conversations"]:
                if conv["id"] == conversation_id:
                    hook_entry = {
                        "content": hooks_content
                    }
                    
                    if "hooks" not in conv:
                        conv["hooks"] = []
                    
                    conv["hooks"].append(hook_entry)
                    self._save_conversations(data)
                    return True
        return False

    def delete_script(self, conversation_id, script_index):
        data = self._load_conversations()
        
        # Nettoyer les anciennes conversations
        data = self._cleanup_old_conversations(data)
        
        if self.username in data:
            for conv in data[self.username]["conversations"]:
                if conv["id"] == conversation_id:
                    if 0 <= script_index < len(conv["scripts"]):
                        del conv["scripts"][script_index]
                        self._save_conversations(data)
                        return True
        return False

    def delete_hook(self, conversation_id, hook_index):
        data = self._load_conversations()
        
        # Nettoyer les anciennes conversations
        data = self._cleanup_old_conversations(data)
        
        if self.username in data:
            for conv in data[self.username]["conversations"]:
                if conv["id"] == conversation_id:
                    if 0 <= hook_index < len(conv.get("hooks", [])):
                        del conv["hooks"][hook_index]
                        self._save_conversations(data)
                        return True
        return False

    def update_script(self, conversation_id, script_index, new_content):
        data = self._load_conversations()
        
        # Nettoyer les anciennes conversations
        data = self._cleanup_old_conversations(data)
        
        if self.username in data:
            for conv in data[self.username]["conversations"]:
                if conv["id"] == conversation_id:
                    if 0 <= script_index < len(conv["scripts"]):
                        conv["scripts"][script_index]["content"] = new_content
                        conv["scripts"][script_index]["char_count"] = len(new_content)
                        self._save_conversations(data)
                        return True
        return False

    def update_hook(self, conversation_id, hook_index, new_content):
        data = self._load_conversations()
        
        # Nettoyer les anciennes conversations
        data = self._cleanup_old_conversations(data)
        
        if self.username in data:
            for conv in data[self.username]["conversations"]:
                if conv["id"] == conversation_id:
                    if 0 <= hook_index < len(conv.get("hooks", [])):
                        conv["hooks"][hook_index]["content"] = new_content
                        self._save_conversations(data)
                        return True
        return False
    
    def generate_script_stream(self, animal):
        if not self.api_key:
            st.error("❌ Clé API Anthropic non configurée")
            return None
        
        if not self.script_prompt:
            st.error("❌ Prompt script non chargé")
            return None
        
        try:
            if "{{ANIMAL}}" not in self.script_prompt:
                st.error("❌ Le placeholder {{ANIMAL}} n'est pas trouvé dans le prompt!")
                return None

            prompt = self.script_prompt.replace("{{ANIMAL}}", animal)
            
            with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=6500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                
                full_text = ""
                placeholder = st.empty()
                
                for text in stream.text_stream:
                    full_text += text
                    placeholder.markdown(f"{full_text}")
                
                # Incrémenter le compteur de scripts après génération réussie
                if full_text and self.username:
                    auth_manager = AuthManager()
                    auth_manager.increment_script_count(self.username)
                
                return full_text
                
        except Exception as e:
            st.error(f"❌ Erreur génération: {str(e)}")
            return None
    
    def generate_hooks_stream(self, conversation):
        if not self.api_key:
            st.error("❌ Clé API non configurée")
            return None
            
        if not self.hook_prompt:
            st.error("❌ Prompt hook non chargé")
            return None
            
        if not conversation["scripts"]:
            st.warning("⚠️ Aucun script dans la conversation")
            return None
        
        try:
            combined_scripts = "\n\n".join([
                f"SCRIPT {i+1}:\n{script['content']}" 
                for i, script in enumerate(conversation["scripts"])
            ])
            
            prompt = self.hook_prompt.replace("{{SCRIPT}}", f"{combined_scripts}")
            
            with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                
                full_text = ""
                placeholder = st.empty()
                
                for text in stream.text_stream:
                    full_text += text
                    placeholder.markdown(f"{full_text}")
                
                # Incrémenter le compteur de hooks après génération réussie
                if full_text and self.username:
                    auth_manager = AuthManager()
                    auth_manager.increment_hook_count(self.username)
                
                return full_text
                
        except Exception as e:
            st.error(f"❌ Erreur génération hooks: {str(e)}")
            return None

def get_random_animals_placeholder():
    try:
        animals_list = st.secrets.get("ANIMALS_LIST", "")
        if animals_list:
            try:
                animals = json.loads(animals_list)
            except json.JSONDecodeError:
                animals = [line.strip() for line in animals_list.split('\n') if line.strip()]
            
            if animals:
                selected = random.sample(animals, min(10, len(animals)))
                return ", ".join(selected)
    except Exception:
        pass
    
    return "panda, requin, koala, éléphant, girafe, lion, tigre, ours, loup, chat"

def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        return True
    except:
        return False

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("# 🔐 Connexion - Empire Generator")
        with st.container(border=True):
            st.markdown("### Identifiants")
            
            with st.form("login_form"):
                username = st.text_input("Nom d'utilisateur", key="login_username")
                password = st.text_input("Mot de passe", type="password", key="login_password")
                
                login_btn = st.form_submit_button("🔐 Se connecter", type="primary", use_container_width=True)
                
                if login_btn:
                    auth_manager = AuthManager()
                    
                    # Vérifier d'abord si c'est un admin
                    if auth_manager.authenticate_admin(username, password):
                        st.session_state.authenticated = True
                        st.session_state.user_type = "admin"
                        st.session_state.username = username
                        st.rerun()
                    # Ensuite vérifier si c'est un utilisateur normal
                    elif auth_manager.authenticate_user(username, password):
                        st.session_state.authenticated = True
                        st.session_state.user_type = "user"
                        st.session_state.username = username
                        auth_manager.update_last_login(username)
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")

def show_admin_console():
    """Afficher la console d'administration"""
    st.markdown("# Console Administration")
    
    auth_manager = AuthManager()
    
    tab1, tab2, tab3 = st.tabs(["Gestion Utilisateurs", "Statistiques", "Mot de passe"])
    
    with tab1:
        st.markdown("### Ajouter un Utilisateur")
        with st.form("add_user_form"):
            new_username = st.text_input("Nom d'utilisateur")
            initial_credits = st.number_input("Crédits initiaux", min_value=0, max_value=1000, value=30)
            
            if st.form_submit_button("Ajouter", type="primary", use_container_width=True):
                if new_username.strip():
                    if auth_manager.add_user(new_username.strip(), initial_credits):
                        st.rerun()
                    else:
                        st.error("Utilisateur déjà existant")
                else:
                    st.error("Nom d'utilisateur requis")

        st.markdown("### Choisir un Utilisateur")
        users = auth_manager.get_all_users()
        user_options = [""] + list(users.keys()) if users else [""]
        
        user_to_select = st.selectbox(
            "Sélectionner un utilisateur",
            options=user_options,
            key="delete_user_select"
        )

        if user_to_select:
            current_credits = auth_manager.get_user_credits(user_to_select)
            
            new_credits = st.slider(
                "Nouveaux crédits",
                min_value=0,
                max_value=100,
                value=current_credits,
                key=f"credits_slider_{user_to_select}"
            )
            
            if new_credits != current_credits:
                if st.button("Mettre à jour les crédits", type="primary", use_container_width=True):
                    auth_manager.update_user_credits(user_to_select, new_credits)
                    st.rerun()
        
        if user_to_select and st.button("Supprimer", type="secondary", use_container_width=True):
            if auth_manager.remove_user(user_to_select):
                st.rerun()
            else:
                st.error("Erreur lors de la suppression")
    
    with tab2:
        st.markdown("### Liste des Utilisateurs")
        users = auth_manager.get_all_users()
        
        if users:
            total_users = len(users)
            total_credits = sum(user['credits'] for user in users.values())
            active_users = len([u for u in users.values() if u.get('last_login')])
            total_scripts = sum(user.get('total_scripts', 0) for user in users.values())
            total_hooks = sum(user.get('total_hooks', 0) for user in users.values())
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Utilisateurs", total_users)
            
            with col2:
                st.metric("Crédits Totaux", total_credits)
            
            with col3:
                st.metric("Utilisateurs Actifs", active_users)
            
            with col4:
                st.metric("Scripts Générés", total_scripts)
            
            with col5:
                st.metric("Hooks Générés", total_hooks)
            
            # Tableau détaillé avec possibilité de suppression
            st.markdown("### Détails par Utilisateur")
            user_stats = []
            
            def get_user_content_stats(username):
                try:
                    with open("conversations.json", 'r', encoding='utf-8') as f:
                        conv_data = json.load(f)
                        user_conversations = conv_data.get(username, {}).get("conversations", [])
                        scripts_count = sum(len(conv.get("scripts", [])) for conv in user_conversations)
                        hooks_count = sum(len(conv.get("hooks", [])) for conv in user_conversations)
                        return scripts_count, hooks_count
                except:
                    return 0, 0
            
            for username, user_data in users.items():
                # Utiliser les compteurs totaux depuis la base de données utilisateurs
                total_scripts = user_data.get('total_scripts', 0)
                total_hooks = user_data.get('total_hooks', 0)
                
                user_stats.append({
                    "Utilisateur": username,
                    "Crédits": user_data['credits'],
                    "Total Scripts": total_scripts,
                    "Total Hooks": total_hooks,
                    "Dernière connexion": datetime.fromisoformat(user_data['last_login']).strftime("%d/%m %H:%M") if user_data.get('last_login') else "Jamais"
                })
            
            st.dataframe(user_stats, use_container_width=True)
            
        else:
            st.info("Aucun utilisateur enregistré")

    with tab3:
        st.markdown("### Modifier le Mot de Passe Global")
        data = auth_manager._load_users()
        current_password = data.get("global_password", "")
        
        with st.form("password_form"):
            st.info(f"Mot de passe actuel: **{current_password}**")
            new_password = st.text_input("Nouveau mot de passe")
            confirm_password = st.text_input("Confirmer le mot de passe")
            
            if st.form_submit_button("🔄 Changer le mot de passe", type="primary", use_container_width=True):
                if new_password and new_password == confirm_password:
                    auth_manager.update_global_password(new_password)
                    st.rerun()
                elif new_password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas")
                else:
                    st.error("Mot de passe requis")

if 'generated_script' not in st.session_state:
    st.session_state.generated_script = None
if 'generated_animal' not in st.session_state:
    st.session_state.generated_animal = None
if 'show_success_message' not in st.session_state:
    st.session_state.show_success_message = False
if 'generation_in_progress' not in st.session_state:
    st.session_state.generation_in_progress = False
if 'random_animals' not in st.session_state:
    st.session_state.random_animals = get_random_animals_placeholder()
if 'show_manual_form' not in st.session_state:
    st.session_state.show_manual_form = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = "main"
if 'selected_animal' not in st.session_state:
    st.session_state.selected_animal = None
if 'auto_generate' not in st.session_state:
    st.session_state.auto_generate = False
if 'auto_generate_animal' not in st.session_state:
    st.session_state.auto_generate_animal = None

def show_animal_manager_page(animal, generator):
    # Gestion des toasts de sauvegarde et suppression
    if st.session_state.get('show_save_success'):
        st.toast(st.session_state.save_message, icon="✅")
        st.session_state.show_save_success = False
        del st.session_state.save_message
    
    if st.session_state.get('show_save_error'):
        st.toast(st.session_state.error_message, icon="❌")
        st.session_state.show_save_error = False
        del st.session_state.error_message
    
    if st.session_state.get('show_delete_success'):
        st.toast(st.session_state.delete_message, icon="🗑️")
        st.session_state.show_delete_success = False
        del st.session_state.delete_message
    
    if st.session_state.get('show_delete_error'):
        st.toast(st.session_state.delete_error_message, icon="❌")
        st.session_state.show_delete_error = False
        del st.session_state.delete_error_message
    
    
    if st.button("← Retour", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
    
    data = generator._load_conversations()
    # Nettoyer les anciennes conversations avant affichage
    data = generator._cleanup_old_conversations(data)
    conversation = None
    
    user_data = data.get(st.session_state.username, {})
    user_conversations = user_data.get("conversations", [])

    for conv in user_conversations:
        if conv["animal"].lower() == animal.lower():
            conversation = conv
            break
    
    if not conversation:
        st.error(f"❌ Aucune conversation trouvée pour {animal}")
        return
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("#### Scripts")
        if conversation["scripts"]:
            for i, script in enumerate(conversation["scripts"]):
                with st.container():
                    st.text_area(
                        f"**Script {i+1}** ({script['char_count']} caractères)",
                        value=script["content"],
                        height=300,
                        key=f"script_content_{conversation['id']}_{i}",
                        disabled=False
                    )
                    
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                    
                    with col_btn1:
                        if st.button(f"🗑️", key=f"del_script_{conversation['id']}_{i}", use_container_width=True):
                            if generator.delete_script(conversation["id"], i):
                                st.session_state.show_delete_success = True
                                st.session_state.delete_message = "Script supprimé"
                                st.rerun()
                            else:
                                st.session_state.show_delete_error = True
                                st.session_state.delete_error_message = "Erreur lors de la suppression"
                                st.rerun()
                    
                    with col_btn2:
                        if st.button(f"➕", key=f"add_script_{conversation['id']}_{i}", use_container_width=True):
                            if "mix_content" not in st.session_state:
                                st.session_state.mix_content = ""
                            st.session_state.mix_content += f"\n\n{script['content']}"
                    
                    with col_btn3:
                        if st.button(f"Sauvegarder", type="primary", key=f"save_script_{conversation['id']}_{i}", use_container_width=True):
                            # Récupérer le contenu modifié
                            modified_content = st.session_state.get(f"script_content_{conversation['id']}_{i}", script["content"])
                            if generator.update_script(conversation["id"], i, modified_content):
                                st.session_state.show_save_success = True
                                st.session_state.save_message = "Script mis à jour"
                                st.rerun()
                            else:
                                st.session_state.show_save_error = True
                                st.session_state.error_message = "Erreur lors de la sauvegarde"
                                st.rerun()
                    
        else:
            st.container(height=5, border=False)
            st.text("Aucun script pour cet animal...")
            
            # Vérifier les crédits pour la génération
            if st.session_state.user_type == "user":
                auth_manager = AuthManager()
                user_credits = auth_manager.get_user_credits(st.session_state.username)
                
                if user_credits >= 2:
                    if st.button(f"Générer un script - 2/{user_credits} crédits", type="primary", key=f"generate_script_{conversation['id']}", use_container_width=True):
                        if auth_manager.deduct_credits(st.session_state.username, 2):
                            with st.spinner("Génération du script en cours..."):
                                generated_script = generator.generate_script_stream(conversation["animal"])
                                if generated_script:
                                    if generator.add_script_to_conversation(conversation["animal"], generated_script):
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de l'ajout du script")
                                else:
                                    st.error("❌ Erreur lors de la génération du script")
                                    # Rembourser les crédits en cas d'erreur
                                    auth_manager.update_user_credits(st.session_state.username, user_credits)
                        else:
                            st.error("❌ Crédits insuffisants")
                else:
                    st.button(f"Crédits insuffisants - {user_credits}/2", type="primary", key=f"generate_script_{conversation['id']}", use_container_width=True, disabled=True)
            else:  # Admin
                if st.button("Générer un script", type="primary", key=f"generate_script_{conversation['id']}", use_container_width=True):
                    with st.spinner("Génération du script en cours..."):
                        generated_script = generator.generate_script_stream(conversation["animal"])
                        if generated_script:
                            if generator.add_script_to_conversation(conversation["animal"], generated_script):
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de l'ajout du script")
                        else:
                            st.error("❌ Erreur lors de la génération du script")
            
            if st.button("Ajouter un script manuellement", key=f"add_manual_script_{conversation['id']}", use_container_width=True):
                st.session_state[f"show_manual_script_form_{conversation['id']}"] = True
                st.rerun()
            
            if st.session_state.get(f"show_manual_script_form_{conversation['id']}", False):
                st.markdown("#### Ajout manuel de script")
                
                with st.form(key=f"manual_script_form_{conversation['id']}"):
                    manual_script = st.text_area(
                        "Script",
                        placeholder="Entrez votre script ici...",
                        height=400,
                        key=f"manual_script_input_{conversation['id']}"
                    )
                    
                    col_submit, col_cancel = st.columns([1, 1])
                    
                    with col_submit:
                        submit_manual = st.form_submit_button("✅ Valider", type="primary", use_container_width=True)
                    
                    with col_cancel:
                        cancel_manual = st.form_submit_button("❌ Annuler", use_container_width=True)
                    
                    if submit_manual and manual_script.strip():
                        success = generator.add_script_to_conversation(
                            conversation["animal"], 
                            manual_script.strip()
                        )
                        if success:
                            st.session_state[f"show_manual_script_form_{conversation['id']}"] = False
                            st.rerun()
                        else:
                            st.error("Erreur lors de la sauvegarde")
                    elif submit_manual:
                        st.error("Le script ne peut pas être vide")
                    
                    if cancel_manual:
                        st.session_state[f"show_manual_script_form_{conversation['id']}"] = False
                        st.rerun()
    
    with col2:
        st.markdown("#### Zone de Mix")
        
        if "mix_content" not in st.session_state:
            st.session_state.mix_content = ""
        
        mix_content = st.text_area(
            f"**Zone de Mix** ({len(st.session_state.mix_content)} caractères)",
            label_visibility="visible",
            value=st.session_state.mix_content,
            height=300,
            placeholder="Votre contenu mixé apparaîtra ici...",
            key="mix_textarea"
        )
        
        if mix_content != st.session_state.get("mix_content", ""):
            st.session_state.mix_content = mix_content
            st.rerun()
        
        col_mix1, col_mix2 = st.columns([1, 1])
        
        with col_mix1:
            if st.button("📋", key="copy_mix", use_container_width=True):
                if copy_to_clipboard(mix_content):
                    st.toast("Mix copié dans le presse-papiers")
                else:
                    st.toast("Erreur lors de la copie")
        
        with col_mix2:
            if st.button("Vider le mix", key="clear_mix", type="primary", use_container_width=True):
                st.session_state.mix_content = ""
                st.rerun()

    with col3:
        st.markdown("#### Hooks")
        if conversation.get("hooks"):
            for i, hook in enumerate(conversation["hooks"]):
                with st.container():
                    st.text_area(
                        f"**Hooks {i+1}** ({len(hook['content'])} caractères)",
                        value=hook["content"],
                        height=300,
                        key=f"hook_content_{conversation['id']}_{i}",
                        disabled=False
                    )
                    
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                    
                    with col_btn1:
                        if st.button(f"🗑️", key=f"del_hook_{conversation['id']}_{i}", use_container_width=True):
                            if generator.delete_hook(conversation["id"], i):
                                st.session_state.show_delete_success = True
                                st.session_state.delete_message = "Hooks supprimés"
                                st.rerun()
                            else:
                                st.session_state.show_delete_error = True
                                st.session_state.delete_error_message = "Erreur lors de la suppression"
                                st.rerun()
                    
                    with col_btn2:
                        if st.button(f"➕", key=f"add_hook_{conversation['id']}_{i}", use_container_width=True):
                            if "mix_content" not in st.session_state:
                                st.session_state.mix_content = ""
                            st.session_state.mix_content += f"{hook['content']}"
                            st.rerun()
                    
                    with col_btn3:
                        if st.button(f"Sauvegarder", type="primary", key=f"save_hook_{conversation['id']}_{i}", use_container_width=True):
                            modified_content = st.session_state.get(f"hook_content_{conversation['id']}_{i}", hook["content"])
                            if generator.update_hook(conversation["id"], i, modified_content):
                                st.session_state.show_save_success = True
                                st.session_state.save_message = "Hooks mis à jour"
                                st.rerun()
                            else:
                                st.session_state.show_save_error = True
                                st.session_state.error_message = "Erreur lors de la sauvegarde"
                                st.rerun()
                    
        else:
            st.container(height=5, border=False)
            st.text("Aucun hook pour cet animal...")
            
            # Vérifier les crédits pour la génération de hooks
            if st.session_state.user_type == "user":
                auth_manager = AuthManager()
                user_credits = auth_manager.get_user_credits(st.session_state.username)
                
                if user_credits >= 1:
                    if st.button(f"Générer des hooks - 1/{user_credits} crédits", type="primary", key=f"generate_hooks_{conversation['id']}", use_container_width=True):
                        if auth_manager.deduct_credits(st.session_state.username, 1):
                            with st.spinner("Génération des hooks en cours..."):
                                generated_hooks = generator.generate_hooks_stream(conversation)
                                if generated_hooks:
                                    if generator.add_hooks_to_conversation(conversation["id"], generated_hooks):
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de l'ajout des hooks")
                                else:
                                    st.error("❌ Erreur lors de la génération des hooks")
                                    # Rembourser les crédits en cas d'erreur
                                    auth_manager.update_user_credits(st.session_state.username, user_credits)
                        else:
                            st.error("❌ Crédits insuffisants")
                else:
                    st.button(f"Crédits insuffisants - {user_credits}/1", type="primary", key=f"generate_hooks_{conversation['id']}", use_container_width=True, disabled=True)
            else:  # Admin
                if st.button("Générer des hooks", type="primary", key=f"generate_hooks_{conversation['id']}", use_container_width=True):
                    with st.spinner("Génération des hooks en cours..."):
                        generated_hooks = generator.generate_hooks_stream(conversation)
                        if generated_hooks:
                            if generator.add_hooks_to_conversation(conversation["id"], generated_hooks):
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de l'ajout des hooks")
                        else:
                            st.error("❌ Erreur lors de la génération des hooks")
            
            if st.button("Ajouter des hooks manuellement", key=f"add_manual_hooks_{conversation['id']}", use_container_width=True):
                st.session_state[f"show_manual_hooks_form_{conversation['id']}"] = True
                st.rerun()
            
            if st.session_state.get(f"show_manual_hooks_form_{conversation['id']}", False):
                st.markdown("#### Ajout manuel de hooks")
                
                with st.form(key=f"manual_hooks_form_{conversation['id']}"):
                    manual_hooks = st.text_area(
                        "Hooks",
                        placeholder="Entrez vos hooks ici...",
                        height=400,
                        key=f"manual_hooks_input_{conversation['id']}"
                    )
                    
                    col_submit, col_cancel = st.columns([1, 1])
                    
                    with col_submit:
                        submit_manual = st.form_submit_button("✅ Valider", type="primary", use_container_width=True)
                    
                    with col_cancel:
                        cancel_manual = st.form_submit_button("❌ Annuler", use_container_width=True)
                    
                    if submit_manual and manual_hooks.strip():
                        success = generator.add_hooks_to_conversation(
                            conversation["id"], 
                            manual_hooks.strip()
                        )
                        if success:
                            st.session_state[f"show_manual_hooks_form_{conversation['id']}"] = False
                            st.rerun()
                        else:
                            st.error("Erreur lors de la sauvegarde")
                    elif submit_manual:
                        st.error("Les hooks ne peuvent pas être vides")
                    
                    if cancel_manual:
                        st.session_state[f"show_manual_hooks_form_{conversation['id']}"] = False
                        st.rerun() 

def main():
    # Initialiser les variables de session
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'generated_script' not in st.session_state:
        st.session_state.generated_script = None
    if 'generated_animal' not in st.session_state:
        st.session_state.generated_animal = None
    if 'show_success_message' not in st.session_state:
        st.session_state.show_success_message = False
    if 'generation_in_progress' not in st.session_state:
        st.session_state.generation_in_progress = False
    if 'random_animals' not in st.session_state:
        st.session_state.random_animals = get_random_animals_placeholder()
    if 'show_manual_form' not in st.session_state:
        st.session_state.show_manual_form = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "main"
    if 'selected_animal' not in st.session_state:
        st.session_state.selected_animal = None
    if 'auto_generate' not in st.session_state:
        st.session_state.auto_generate = False
    if 'auto_generate_animal' not in st.session_state:
        st.session_state.auto_generate_animal = None

    # Si non authentifié, afficher la page de connexion
    if not st.session_state.authenticated:
        show_login_page()
        return

    # Créer le générateur selon le type d'utilisateur
    generator = ViralScriptGenerator(st.session_state.username)

    # Gestion de la sidebar pour l'admin uniquement
    if st.session_state.user_type == "admin":
        with st.sidebar:
            if st.button("🔓 Se déconnecter", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_type = None
                st.session_state.username = None
                st.rerun()
            
            st.markdown("---")
            
            # Navigation admin
            if st.button("Application", use_container_width=True, type="primary" if st.session_state.current_page == "main" else "secondary"):
                st.session_state.current_page = "main"
                st.rerun()
            
            if st.button("Console Admin", use_container_width=True, type="primary" if st.session_state.current_page == "admin_console" else "secondary"):
                st.session_state.current_page = "admin_console"
                st.rerun()
            
            st.markdown("---")
            
            # Status technique
            st.markdown("### Configuration")
            if generator.api_key:
                st.success("✅ API Claude connectée")
            else:
                st.error("❌ API Claude non configurée")
            
            if generator.script_prompt:
                st.success("✅ Script prompt chargé")
            else:
                st.error("❌ Script prompt manquant")
                
            if generator.hook_prompt:
                st.success("✅ Hook prompt chargé")
            else:
                st.error("❌ Hook prompt manquant")

            if generator.animals_list:
                st.success("✅ Liste d'animaux chargée")
            else:
                st.error("❌ Liste d'animaux manquante")
            
            if st.button("Recharger les prompts", use_container_width=True):
                st.rerun()
            
            if st.button("Nettoyer la database", use_container_width=True):
                if st.session_state.get('confirm_delete'):
                    generator.force_cleanup()
                    st.success("✅ Conversations expirées supprimées")
                    st.session_state.confirm_delete = False
                    st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.warning("⚠️ Cliquez à nouveau pour confirmer")

    if st.session_state.user_type == "user":
        auth_manager = AuthManager()
        user_stats = auth_manager.get_user_stats(st.session_state.username)
        
        # Sidebar pour les utilisateurs
        with st.sidebar:
            st.markdown(f"### {st.session_state.username} - {user_stats['credits']} crédits")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Scripts générés", user_stats['total_scripts'])
            with col2:
                st.metric("Hooks générés", user_stats['total_hooks'])
            
            if st.button("Déconnexion", use_container_width=True, type="primary"):
                st.session_state.authenticated = False
                st.session_state.user_type = None
                st.session_state.username = None
                st.rerun()
            
            if st.button("Supprimer mes scripts", use_container_width=True):
                if st.session_state.get('user_confirm_delete'):
                    data = generator._load_conversations()
                    if st.session_state.username in data:
                        data[st.session_state.username] = {"conversations": []}
                        generator._save_conversations(data)
                    st.session_state.user_confirm_delete = False
                    st.rerun()
                else:
                    st.session_state.user_confirm_delete = True
                    st.warning("⚠️ Cliquez à nouveau pour confirmer")

    # Routage des pages
    if st.session_state.current_page == "admin_console" and st.session_state.user_type == "admin":
        show_admin_console()
    elif st.session_state.current_page == "animal_manager":
        if st.session_state.selected_animal:
            show_animal_manager_page(st.session_state.selected_animal, generator)
    else:
        show_main_app(generator)

def show_main_app(generator):
    """Afficher l'application principale"""
    
    if st.session_state.show_success_message:
        st.toast("Script accepté !", icon="🎉")
        st.session_state.show_success_message = False
    
    col1, col2, col3 = st.columns([1, 4, 1])
    generate_btn = None
    
    with col2:
        with st.form(key="main_generation_form", border=False):
            animal_input = st.text_input(
                label="Choix de l'animal",
                label_visibility="hidden",
                placeholder=f"Ex: {st.session_state.random_animals}",
                key="animal_input",
            )
            
            col_btn1, col_btn2, col_btn3 = st.columns([4, 1, 1])
            
            with col_btn1:
                # Affichage différent selon le type d'utilisateur
                if st.session_state.user_type == "user":
                    auth_manager = AuthManager()
                    user_credits = auth_manager.get_user_credits(st.session_state.username)
                    if user_credits >= 2:
                        generate_btn = st.form_submit_button(f"Générer Script - 2/{user_credits} crédits", type="primary", use_container_width=True)
                    else:
                        st.form_submit_button(f"Crédits insuffisants - {user_credits}/2", type="primary", use_container_width=True, disabled=True)
                        generate_btn = None  # Empêcher la génération
                else:  # Admin
                    generate_btn = st.form_submit_button("Générer Script", type="primary", use_container_width=True)
            
            with col_btn2:
                random_btn = st.form_submit_button("🎲", use_container_width=True)
            
            with col_btn3:
                add_manual_btn = st.form_submit_button("➕", use_container_width=True)
        
        if random_btn:
            st.session_state.random_animals = get_random_animals_placeholder()
            st.rerun()
        
        if add_manual_btn:
            st.session_state.show_manual_form = True
            st.rerun()
    
    # Vérifier si on doit générer automatiquement
    if st.session_state.auto_generate and st.session_state.auto_generate_animal:
        animal = st.session_state.auto_generate_animal
        st.session_state.auto_generate = False
        st.session_state.auto_generate_animal = None
        
        if st.session_state.user_type == "user":
            auth_manager = AuthManager()
            if not auth_manager.deduct_credits(st.session_state.username, 2):
                st.error("❌ Crédits insuffisants")
                return
        
        st.session_state.generation_in_progress = True
        
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col2:
            st.markdown(f"#### Génération pour : **{animal}**")
            
            try:
                generated_script = generator.generate_script_stream(animal)
                
                if generated_script:
                    st.session_state.generated_script = generated_script
                    st.session_state.generated_animal = animal
                    st.session_state.generation_in_progress = False
                else:
                    st.session_state.generation_in_progress = False
                    st.error("❌ Échec de la génération du script")
                    # Rembourser en cas d'erreur
                    if st.session_state.user_type == "user":
                        current_credits = auth_manager.get_user_credits(st.session_state.username)
                        auth_manager.update_user_credits(st.session_state.username, current_credits + 2)
            except Exception as e:
                st.session_state.generation_in_progress = False
                st.error(f"❌ Erreur lors de la génération: {str(e)}")
                # Rembourser en cas d'erreur
                if st.session_state.user_type == "user":
                    current_credits = auth_manager.get_user_credits(st.session_state.username)
                    auth_manager.update_user_credits(st.session_state.username, current_credits + 2)
    
    elif generate_btn and animal_input.strip():
        animal = animal_input.strip().title()
        
        if st.session_state.user_type == "user":
            auth_manager = AuthManager()
            if not auth_manager.deduct_credits(st.session_state.username, 2):
                st.error("❌ Crédits insuffisants")
                return
        
        st.session_state.generation_in_progress = True
        
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col2:
            st.markdown(f"#### Génération pour : **{animal}**")
            
            try:
                generated_script = generator.generate_script_stream(animal)
                
                if generated_script:
                    st.session_state.generated_script = generated_script
                    st.session_state.generated_animal = animal
                    st.session_state.generation_in_progress = False
                else:
                    st.session_state.generation_in_progress = False
                    st.error("❌ Échec de la génération du script")
                    # Rembourser en cas d'erreur
                    if st.session_state.user_type == "user":
                        current_credits = auth_manager.get_user_credits(st.session_state.username)
                        auth_manager.update_user_credits(st.session_state.username, current_credits + 2)
            except Exception as e:
                st.session_state.generation_in_progress = False
                st.error(f"❌ Erreur lors de la génération: {str(e)}")
                # Rembourser en cas d'erreur
                if st.session_state.user_type == "user":
                    current_credits = auth_manager.get_user_credits(st.session_state.username)
                    auth_manager.update_user_credits(st.session_state.username, current_credits + 2)
    
    # Formulaire d'ajout manuel
    if st.session_state.show_manual_form:
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col2:
            st.markdown("---")
            st.markdown("#### Ajout manuel de script")
            
            with st.form("manual_script_form"):
                manual_animal = st.text_input(
                    "Animal",
                    placeholder="Ex: Panda, Lion, Chat...",
                    key="manual_animal_input"
                )
                
                manual_script = st.text_area(
                    "Script",
                    placeholder="Entrez votre script ici...",
                    height=200,
                    key="manual_script_input"
                )
                
                col_submit, col_cancel = st.columns([1, 1])
                
                with col_submit:
                    submit_manual = st.form_submit_button("✅ Valider", type="primary", use_container_width=True)
                
                with col_cancel:
                    cancel_manual = st.form_submit_button("❌ Annuler", use_container_width=True)
                
                if submit_manual and manual_animal.strip() and manual_script.strip():
                    success = generator.add_script_to_conversation(
                        manual_animal.strip().title(), 
                        manual_script.strip()
                    )
                    if success:
                        st.session_state.show_manual_form = False
                        st.session_state.show_success_message = True
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la sauvegarde")
                elif submit_manual:
                    st.error("❌ Veuillez remplir tous les champs")
                
                if cancel_manual:
                    st.session_state.show_manual_form = False
                    st.rerun()
    
    # Affichage du script généré
    if st.session_state.generated_script and st.session_state.generated_animal:        
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col2:
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            
            with btn_col1:
                if st.button("✅ Accepter", type="primary", use_container_width=True, key="accept_script_btn"):
                    success = generator.add_script_to_conversation(
                        st.session_state.generated_animal, 
                        st.session_state.generated_script
                    )
                    if success:
                        st.session_state.show_success_message = True
                        st.session_state.generated_script = None
                        st.session_state.generated_animal = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la sauvegarde")
            
            with btn_col2:
                if st.button("❌ Refuser", use_container_width=True, key="reject_script_btn"):
                    st.session_state.generated_script = None
                    st.session_state.generated_animal = None
                    st.warning("Script rejeté.")
                    st.rerun()
            
            with btn_col3:
                # Vérifier les crédits pour une nouvelle version
                can_generate_new = True
                if st.session_state.user_type == "user":
                    auth_manager = AuthManager()
                    user_credits = auth_manager.get_user_credits(st.session_state.username)
                    can_generate_new = user_credits >= 2
                
                if can_generate_new:
                    if st.button("🔄 Nouvelle Version", use_container_width=True, key="new_version_btn"):
                        success = generator.add_script_to_conversation(
                            st.session_state.generated_animal, 
                            st.session_state.generated_script
                        )
                        
                        if success:
                            current_animal = st.session_state.generated_animal
                            
                            st.session_state.generated_script = None
                            st.session_state.generated_animal = None
                            
                            st.session_state.auto_generate_animal = current_animal
                            st.session_state.auto_generate = True
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la sauvegarde")
                else:
                    st.button("🔄 Crédits insuffisants", use_container_width=True, disabled=True)
    
    data = generator._load_conversations()
    # Nettoyer les anciennes conversations avant affichage
    data = generator._cleanup_old_conversations(data)
    user_conversations = data.get(st.session_state.username, {}).get("conversations", [])
    conversations_with_scripts = [conv for conv in user_conversations if conv["scripts"]]
    
    if conversations_with_scripts:
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.container(height=10, border=False)
            
            total_scripts = sum(len(conv["scripts"]) for conv in conversations_with_scripts)
            total_hooks = sum(len(conv.get("hooks", [])) for conv in conversations_with_scripts)
            
            with st.expander(f"📊 Base de données - {total_scripts} scripts, {total_hooks} hooks", expanded=True):
                # Ajouter le temps restant dans les noms d'onglets
                tab_names = []
                for conv in conversations_with_scripts:
                    time_info = generator.get_conversation_time_info(conv)
                    if time_info:
                        tab_names.append(f"{conv['animal']} ({len(conv['scripts'])}) - {time_info}")
                    else:
                        tab_names.append(f"{conv['animal']} ({len(conv['scripts'])})")
                
                tabs = st.tabs(tab_names)
                
                for i, conv in enumerate(conversations_with_scripts):
                    with tabs[i]:
                        display_conversation(conv, generator)

def display_conversation(conversation, generator):
    """Afficher une conversation dans l'onglet"""
    animal = conversation["animal"]
    scripts = conversation["scripts"]
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        script_count = len(scripts)
        script_text = "script" if script_count == 1 else "scripts"
        accepte_text = "accepté" if script_count == 1 else "acceptés"
        st.markdown(f"#### **{animal}** - {script_count} {script_text} {accepte_text}")
    
    with col2:
        if scripts:
            # Vérifier les crédits pour générer des hooks
            can_generate_hooks = True
            hook_button_text = "Générer Hooks"
            
            if st.session_state.user_type == "user":
                auth_manager = AuthManager()
                user_credits = auth_manager.get_user_credits(st.session_state.username)
                can_generate_hooks = user_credits >= 1
                hook_button_text = f"Générer Hooks - 1/{user_credits} crédits" if can_generate_hooks else f"Crédits insuffisants - {user_credits}/1"
            
            generate_hooks_btn = st.button(
                hook_button_text, 
                type="secondary", 
                use_container_width=True,
                key=f"hooks_{conversation['id']}",
                disabled=not can_generate_hooks
            )
    
    with col3:
        if scripts:
            manage_btn = st.button(
                f"Laboratoire", 
                type="primary", 
                use_container_width=True,
                key=f"manage_{conversation['id']}"
            )
            
            if manage_btn:
                st.session_state.current_page = "animal_manager"
                st.session_state.selected_animal = animal
                st.rerun()
    
    # Affichage des scripts
    for i, script in enumerate(scripts, 1):
        with st.expander(f"Script {i} ({script['char_count']} caractères)", expanded=True):
            st.markdown(script["content"])
    
    # Génération des hooks
    if 'generate_hooks_btn' in locals() and generate_hooks_btn and can_generate_hooks:
        # Vérification supplémentaire des crédits
        if st.session_state.user_type == "user":
            auth_manager = AuthManager()
            user_credits = auth_manager.get_user_credits(st.session_state.username)
            if user_credits < 1:
                st.error("❌ Crédits insuffisants")
                return
            
            # Déduire les crédits pour les utilisateurs normaux
            if not auth_manager.deduct_credits(st.session_state.username, 1):
                st.error("❌ Crédits insuffisants")
                return
        
        st.markdown("#### Génération des Hooks")
        
        hooks_content = generator.generate_hooks_stream(conversation)
        
        if hooks_content:
            generator.add_hooks_to_conversation(conversation["id"], hooks_content)
            st.rerun()
        else:
            # Rembourser en cas d'erreur
            if st.session_state.user_type == "user":
                current_credits = auth_manager.get_user_credits(st.session_state.username)
                auth_manager.update_user_credits(st.session_state.username, current_credits + 1)
    
    # Affichage des hooks existants
    if conversation.get("hooks") and len(conversation["hooks"]) > 0:
        st.markdown("#### Hooks Générés")
        
        for i, hook_entry in enumerate(conversation["hooks"], 1):
            with st.expander(f"Hooks {i} - ({len(hook_entry['content'])} caractères)", expanded=True):
                st.markdown(hook_entry["content"])

if __name__ == "__main__":
    main()