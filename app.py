import streamlit as st
import anthropic
import json
import uuid
import os
import time
import random
import pyperclip

# Configuration de la page
st.set_page_config(
    page_title="Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

class ViralScriptGenerator:
    def __init__(self):
        self.api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        self.db_file = "conversations.json"
        
        # Initialiser le fichier de base de données s'il n'existe pas
        if not os.path.exists(self.db_file):
            initial_data = {"conversations": []}
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
                return {"conversations": []}
        return {"conversations": []}
    
    def _save_conversations(self, data):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            raise e
    
    def _get_or_create_conversation(self, animal):
        data = self._load_conversations()
        
        for conv in data["conversations"]:
            if conv["animal"].lower() == animal.lower():
                return conv
        
        new_conv = {
            "id": str(uuid.uuid4()),
            "animal": animal,
            "scripts": [],
            "hooks": []
        }
        
        data["conversations"].append(new_conv)
        self._save_conversations(data)
        return new_conv
    
    def add_hooks_to_conversation(self, conversation_id, hooks_content):
        data = self._load_conversations()
        
        for conv in data["conversations"]:
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
    
    def add_script_to_conversation(self, animal, script_content):
        try:
            data = self._load_conversations()
            
            for conv in data["conversations"]:
                if conv["animal"].lower() == animal.lower():
                    script_entry = {
                        "content": script_content,
                        "char_count": len(script_content)
                    }
                    conv["scripts"].append(script_entry)
                    self._save_conversations(data)
                    return True
            
            new_conv = {
                "id": str(uuid.uuid4()),
                "animal": animal,
                "scripts": [{
                    "content": script_content,
                    "char_count": len(script_content)
                }],
                "hooks": []
            }
            
            data["conversations"].append(new_conv)
            self._save_conversations(data)
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False
    
    def delete_script(self, conversation_id, script_index):
        data = self._load_conversations()
        
        for conv in data["conversations"]:
            if conv["id"] == conversation_id:
                if 0 <= script_index < len(conv["scripts"]):
                    del conv["scripts"][script_index]
                    self._save_conversations(data)
                    return True
        return False
    
    def delete_hook(self, conversation_id, hook_index):
        data = self._load_conversations()
        
        for conv in data["conversations"]:
            if conv["id"] == conversation_id:
                if 0 <= hook_index < len(conv.get("hooks", [])):
                    del conv["hooks"][hook_index]
                    self._save_conversations(data)
                    return True
        return False
    
    def update_script(self, conversation_id, script_index, new_content):
        data = self._load_conversations()
        
        for conv in data["conversations"]:
            if conv["id"] == conversation_id:
                if 0 <= script_index < len(conv["scripts"]):
                    conv["scripts"][script_index]["content"] = new_content
                    conv["scripts"][script_index]["char_count"] = len(new_content)
                    self._save_conversations(data)
                    return True
        return False
    
    def update_hook(self, conversation_id, hook_index, new_content):
        data = self._load_conversations()
        
        for conv in data["conversations"]:
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
                
                return full_text
                
        except Exception as e:
            st.error(f"❌ Erreur génération hooks: {str(e)}")
            return None

@st.cache_resource
def get_generator():
    return ViralScriptGenerator()

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

generator = get_generator()

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

def show_animal_manager_page(animal):
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
    conversation = None
    
    for conv in data["conversations"]:
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
                    
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
                    
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
                        if st.button(f"📋", key=f"copy_script_{conversation['id']}_{i}", use_container_width=True):
                            if copy_to_clipboard(script["content"]):
                                st.toast("Script copié dans le presse-papiers")
                            else:
                                st.toast("Erreur lors de la copie")
                    
                    with col_btn3:
                        if st.button(f"➕", key=f"add_script_{conversation['id']}_{i}", use_container_width=True):
                            if "mix_content" not in st.session_state:
                                st.session_state.mix_content = ""
                            st.session_state.mix_content += f"\n\n{script['content']}"
                    
                    with col_btn4:
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
            # Mettre à jour le titre avec le nouveau nombre de caractères
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
                    
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
                    
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
                        if st.button(f"📋", key=f"copy_hook_{conversation['id']}_{i}", use_container_width=True):
                            if copy_to_clipboard(hook["content"]):
                                st.toast("Hooks copiés dans le presse-papiers")
                            else:
                                st.toast("Erreur lors de la copie")
                    
                    with col_btn3:
                        if st.button(f"➕", key=f"add_hook_{conversation['id']}_{i}", use_container_width=True):
                            if "mix_content" not in st.session_state:
                                st.session_state.mix_content = ""
                            st.session_state.mix_content += f"{hook['content']}"
                            st.rerun()
                    
                    with col_btn4:
                        if st.button(f"Sauvegarder", type="primary", key=f"save_hook_{conversation['id']}_{i}", use_container_width=True):
                            # Récupérer le contenu modifié
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
            if st.button(type="primary", key=f"generate_hooks_{conversation['id']}", use_container_width=True, label="Générer des hooks"):
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
    if st.session_state.current_page == "animal_manager":
        if st.session_state.selected_animal:
            show_animal_manager_page(st.session_state.selected_animal)
        return
    
    if st.session_state.show_success_message:
        st.toast("Script accepté !", icon="🎉")
        st.session_state.show_success_message = False
    
    col1, col2, col3 = st.columns([1, 3, 1])
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
                generate_btn = st.form_submit_button("Générer Script", type="primary", use_container_width=True)
            
            with col_btn2:
                random_btn = st.form_submit_button("🎲", use_container_width=True)
            
            with col_btn3:
                add_manual_btn = st.form_submit_button("➕", use_container_width=True)
        
        # Gestion des boutons en dehors du formulaire
        if random_btn:
            st.session_state.random_animals = get_random_animals_placeholder()
            st.rerun()
        
        if add_manual_btn:
            st.session_state.show_manual_form = True
            st.rerun()
    
    # Vérifier si on doit générer automatiquement (après "Nouvelle Version")
    if st.session_state.auto_generate and st.session_state.auto_generate_animal:
        animal = st.session_state.auto_generate_animal
        st.session_state.auto_generate = False  # Reset pour éviter les boucles
        st.session_state.auto_generate_animal = None  # Reset pour éviter les boucles
        
        st.session_state.generation_in_progress = True
        
        col1, col2, col3 = st.columns([1, 3, 1])
        
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
            except Exception as e:
                st.session_state.generation_in_progress = False
                st.error(f"❌ Erreur lors de la génération: {str(e)}")
    
    elif generate_btn and animal_input.strip():
        animal = animal_input.strip().title()
        
        st.session_state.generation_in_progress = True
        
        col1, col2, col3 = st.columns([1, 3, 1])
        
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
            except Exception as e:
                st.session_state.generation_in_progress = False
                st.error(f"❌ Erreur lors de la génération: {str(e)}")
    
    if st.session_state.show_manual_form:
        col1, col2, col3 = st.columns([1, 3, 1])
        
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
    
    if st.session_state.generated_script and st.session_state.generated_animal:        
        col1, col2, col3 = st.columns([1, 3, 1])
        
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
                        # Nettoyer le script généré
                        st.session_state.generated_script = None
                        st.session_state.generated_animal = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la sauvegarde")
            
            with btn_col2:
                if st.button("❌ Refuser", use_container_width=True, key="reject_script_btn"):
                    st.session_state.generated_script = None
                    st.session_state.generated_animal = None
                    st.warning("Script rejeté. Essayez un autre animal ou relancez.")
                    st.rerun()
            
            with btn_col3:
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
    
    data = generator._load_conversations()
    conversations_with_scripts = [conv for conv in data["conversations"] if conv["scripts"]]
    
    if conversations_with_scripts:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.container(height=10, border=False)
            
            total_scripts = sum(len(conv["scripts"]) for conv in conversations_with_scripts)
            total_hooks = sum(len(conv.get("hooks", [])) for conv in conversations_with_scripts)
            
            with st.expander(f"📊 Base de données - {total_scripts} scripts, {total_hooks} hooks", expanded=True):
                tab_names = [f"{conv['animal']} ({len(conv['scripts'])})" for conv in conversations_with_scripts]
                tabs = st.tabs(tab_names)
                
                for i, conv in enumerate(conversations_with_scripts):
                    with tabs[i]:
                        display_conversation(conv, generator)

def display_conversation(conversation, generator):
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
            generate_hooks_btn = st.button(
                f"🎯 Générer Hooks", 
                type="secondary", 
                use_container_width=True,
                key=f"hooks_{conversation['id']}"
            )
    
    with col3:
        if scripts:
            manage_btn = st.button(
                f"⚙️ Gérer", 
                type="primary", 
                use_container_width=True,
                key=f"manage_{conversation['id']}"
            )
            
            if manage_btn:
                st.session_state.current_page = "animal_manager"
                st.session_state.selected_animal = animal
                st.rerun()
    
    for i, script in enumerate(scripts, 1):
        with st.expander(f"Script {i} ({script['char_count']} caractères)", expanded=True):
            st.markdown(script["content"])
    
    if 'generate_hooks_btn' in locals() and generate_hooks_btn:
        st.markdown("#### Génération des Hooks")
        
        hooks_content = generator.generate_hooks_stream(conversation)
        
        if hooks_content:
            generator.add_hooks_to_conversation(conversation["id"], hooks_content)
            st.rerun()
    
    if conversation.get("hooks") and len(conversation["hooks"]) > 0:
        st.markdown("#### Hooks Générés")
        
        for i, hook_entry in enumerate(conversation["hooks"], 1):
            with st.expander(f"Hooks - ({len(hook_entry['content'])} caractères)", expanded=True):
                st.markdown(hook_entry["content"])

with st.sidebar:
    st.markdown("### Configuration")
    # Status API
    if generator.api_key:
        st.success("✅ API Claude connectée")
    else:
        st.error("❌ API Claude non configurée")
    
    # Status des prompts
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
    
    if st.button("🔄 Recharger Prompts", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()
    
    if st.button("🗑️ Nettoyer Database", use_container_width=True):
        if st.session_state.get('confirm_delete'):
            if os.path.exists(generator.db_file):
                os.remove(generator.db_file)
            st.success("✅ Base nettoyée")
            st.session_state.confirm_delete = False
            st.rerun()
        else:
            st.session_state.confirm_delete = True
            st.warning("⚠️ Cliquez à nouveau pour confirmer")

if __name__ == "__main__":
    main()