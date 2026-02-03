import streamlit as st
import httpx
import os
from dotenv import load_dotenv
from groq import Groq
import base64

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Professional README Generator",
    layout="wide"
)

# Custom CSS for premium look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stTextArea>div>div>textarea {
        background-color: white;
        color: black;
    }
    .stTextInput>div>div>input {
        background-color: white;
        color: black;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def fetch_github_repo(repo_url):
    """Fetch repository structure, languages, and existing README."""
    try:
        # Basic parsing of GitHub URL
        parts = repo_url.strip("/").split("/")
        if len(parts) < 2:
            return None, "Invalid GitHub URL"
        
        owner, repo = parts[-2], parts[-1]
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        with httpx.Client() as client:
            # 1. Fetch file list
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
            response = client.get(api_url, headers=headers)
            if response.status_code != 200:
                return None, f"Error fetching repo contents: {response.status_code}"
            
            contents = response.json()
            file_list = [item['name'] for item in contents]
            
            # 2. Fetch Languages
            lang_url = f"https://api.github.com/repos/{owner}/{repo}/languages"
            lang_response = client.get(lang_url, headers=headers)
            languages = lang_response.json() if lang_response.status_code == 200 else {}

            # 3. Fetch Existing README
            readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            readme_response = client.get(readme_url, headers=headers)
            existing_readme = ""
            if readme_response.status_code == 200:
                readme_data = readme_response.json()
                if readme_data.get('content'):
                    # GitHub API returns base64 for file content
                    existing_readme = base64.b64decode(readme_data['content']).decode('utf-8')

            # 4. Fetch Key Config Files
            context_files = {}
            for item in contents:
                if item['type'] == 'file' and item['name'].lower() in ['package.json', 'setup.py', 'requirements.txt', 'main.py', 'app.py']:
                    file_response = client.get(item['download_url'])
                    if file_response.status_code == 200:
                        context_files[item['name']] = file_response.text[:1000]
            
            return {
                "files": file_list, 
                "languages": languages, 
                "existing_readme": existing_readme,
                "context": context_files
            }, None
    except Exception as e:
        return None, str(e)

@st.cache_data(show_spinner=False)
def generate_content(api_key, prompt, system_message):
    if not api_key:
        return "Please provide a valid Groq API Key."
    
    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error during generation: {str(e)}"

def main():
    st.title("Professional README Generator")
    st.markdown("Generate high-quality documentation for your projects in seconds.")

    # Sidebar for Configuration
    with st.sidebar:
        st.header("Settings")
        st.success("API Key loaded from environment" if os.getenv("GROQ_API_KEY") else "API Key missing in environment")
        api_key = os.getenv("GROQ_API_KEY", "")
        
        st.divider()
        st.markdown("### How it works")
        st.write("1. Provide a project description OR a GitHub URL.")
        st.write("2. Click 'Generate' to create your documentation.")
        st.write("3. Review, edit, and download your README.md.")

    # Main UI Tabs
    tab1, tab2 = st.tabs(["Project Description", "GitHub Repository"])

    with tab1:
        project_title = st.text_input("Project Title", placeholder="e.g. WaterFlow Tracker")
        project_idea = st.text_area("What is your project about?", placeholder="e.g. A web app that tracks daily water intake using React and Firebase...", height=200)
        gen_readme_desc = st.button("Generate Full Documentation", key="gen_readme_idea")
        gen_short_desc = False

    with tab2:
        repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/repo")
        gen_readme_repo = st.button("Generate Full Documentation", key="gen_readme_repo")
        gen_short_repo = False

    # Handle Generation Logic
    output = ""
    prompt = ""
    system_msg = """
    You are a senior software engineer and technical storyteller.
    Your goal is to create a professional GitHub presence and career impact statement for a project.

    You MUST provide THREE parts in your response, separated by the headers exactly as shown below:

    === GITHUB_DESCRIPTION ===
    [A concise 1-2 line summary for the GitHub "About" field]

    === RESUME_BULLET ===
    [Project Title] | [Tech Stack: e.g. React, Node.js, Firebase]
    • [Significant impact-driven bullet point 1]
    • [Significant impact-driven bullet point 2]
    • [Optional: impact-driven bullet point 3]

    === README ===
    [Your Narrative README.md starts here]

    ADMIN RULES FOR THE README:
    - Section titles must be meaningful and domain-specific (Example: use "What is Churn?" instead of "What This Project Does").
    - Maintain a clear narrative flow: Problem → Concept → Solution → System → Impact.
    - Use Markdown with occasional HTML (<ul>, <li>, <b>) for structured sections.
    - DO NOT use any emojis.
    - DO NOT hallucinate features or technologies.
    - Provide a professional, recruiter-friendly README that feels like it was written by a lead engineer.

    REQUIRED README STRUCTURE (ADAPT HEADINGS BASED ON CONTEXT):
    1. Project Title & Tagline
    2. Project Overview (High-level, domain/users/value)
    3. Problem Statement (Real-world problem, goals)
    4. Domain Concept Explanation (e.g. "What is Churn?", define thresholds/rules)
    5. Technical Overview (System type, models, outputs)
    6. Data Overview (Data representation, time windows, targets)
    7. Key Features Used (Grouped logically)
    8. Product Analytics / System Insights (Patterns, trends revealed)
    9. Single Entity Prediction & Bulk Prediction (As applicable)
    10. Folder Structure (Tree format)
    11. Installation & Setup (Step-by-step)
    12. Future Enhancements (Realistic improvements)
    """

    system_msg_repo = """
    You are a senior software engineer and technical storyteller.
    Analyze the provided GitHub repository details to create professional documentation and resume impact statements.

    You MUST provide THREE parts in your response, separated by the headers exactly as shown below:

    === GITHUB_DESCRIPTION ===
    [A concise 1-2 line summary for the GitHub "About" field]

    === RESUME_BULLET ===
    [Project Title] | [Extract exact tech stack from files: e.g. Python, Scikit-learn, Streamlit]
    • [Professional bullet point 1 using strong action verbs]
    • [Professional bullet point 2 using strong action verbs]
    • [Optional: bullet point 3]

    === README ===
    [Your Narrative README.md starts here]

    ADMIN RULES FOR THE README:
    - Section titles must be meaningful and domain-specific.
    - Maintain a clear narrative flow: Problem → Concept → Solution → System → Impact.
    - If an existing README exists, review and improve it significantly using this narrative approach.
    - Use Markdown with HTML (<ul>, <li>, <b>) for structured sections.
    - DO NOT use any emojis.
    - DO NOT hallucinate features or technologies.
    - Show the project structure using a tree format.
    
    REQUIRED README STRUCTURE (ADAPT HEADINGS BASED ON CONTEXT):
    1. Project Title & Tagline
    2. Project Overview (High-level explanation)
    3. Problem Statement & Goals
    4. Domain Concept Explanation (e.g. "What is [Core Concept]?")
    5. Technical Architecture (Stack, models, outputs)
    6. Key Components & Implementation Details (Based on file analysis)
    7. System Logic / Analytics Insights (Trends revealed by code)
    8. Usage/Workflow (Single/Bulk predictions if detected)
    9. Folder Structure (Tree format)
    10. Installation & Setup (Exact commands from repo analysis)
    11. Future Enhancements

    Generate a professional, recruiter-friendly README that feels like it was written by the lead engineer of the project using the context provided in the user message.
    """

    def parse_combined_output(combined_text):
        desc = ""
        bullet = ""
        readme = ""
        if "=== GITHUB_DESCRIPTION ===" in combined_text and "=== README ===" in combined_text:
            # Extract README
            parts = combined_text.split("=== README ===")
            readme = parts[1].strip()
            
            # Extract Description and Bullet
            pre_readme = parts[0]
            if "=== RESUME_BULLET ===" in pre_readme:
                bullet_parts = pre_readme.split("=== RESUME_BULLET ===")
                bullet = bullet_parts[1].strip()
                desc_parts = bullet_parts[0].split("=== GITHUB_DESCRIPTION ===")
                desc = desc_parts[1].strip()
            else:
                desc_parts = pre_readme.split("=== GITHUB_DESCRIPTION ===")
                desc = desc_parts[1].strip()
        else:
            readme = combined_text # Fallback
        return desc, bullet, readme

    if gen_readme_desc and project_idea:
        with st.spinner("Generating documentation..."):
            title_context = f"Project Title: {project_title}\n" if project_title else ""
            prompt = f"Create documentation for the following project:\n{title_context}Description: {project_idea}"
            output = generate_content(api_key, prompt, system_msg)
            desc, bullet, readme = parse_combined_output(output)
            st.session_state['readme_output'] = readme
            st.session_state['repo_desc'] = desc
            st.session_state['resume_bullet'] = bullet

    elif gen_short_desc and project_idea:
        st.warning("Generate README now includes the short description! Please use 'Generate README'.")

    elif gen_readme_repo and repo_url:
        with st.spinner("Fetching repository data..."):
            repo_data, error = fetch_github_repo(repo_url)
            if error:
                st.error(error)
            else:
                with st.spinner("Analyzing and generating documentation..."):
                    # Prepare technical context
                    languages_str = ", ".join([f"{l} ({count} bytes)" for l, count in repo_data['languages'].items()])
                    context = f"File list: {', '.join(repo_data['files'])}\n"
                    context += f"Languages: {languages_str}\n"
                    
                    if repo_data['existing_readme']:
                        context += f"\n--- EXISTING README.md ---\n{repo_data['existing_readme'][:2000]}\n"
                        instruction = "The repository already has a README. Please IMPROVE it significantly using the provided context."
                    else:
                        instruction = "The repository does NOT have a README. Please CREATE a master-class README from scratch."
                    
                    context += f"\nKey file contents:\n"
                    for name, content in repo_data['context'].items():
                        context += f"\n--- {name} ---\n{content}\n"
                    
                    prompt = f"{instruction}\n\nTechnical details for analysis:\n{context}"
                    output = generate_content(api_key, prompt, system_msg_repo)
                    desc, bullet, readme = parse_combined_output(output)
                    st.session_state['readme_output'] = readme
                    st.session_state['repo_desc'] = desc
                    st.session_state['resume_bullet'] = bullet

    elif gen_short_repo and repo_url:
        st.warning("Generate README now includes the short description! Please use 'Generate README'.")

    # Preview and Download
    if 'readme_output' in st.session_state:
        st.divider()
        st.subheader("Generated Documentation")
        
        # Display Short Description and Resume Bullet if available
        if st.session_state.get('repo_desc'):
            st.markdown("### GitHub Repository Description")
            st.info(st.session_state['repo_desc'])
        
        if st.session_state.get('resume_bullet'):
            st.markdown("### Resume Project Section")
            st.code(st.session_state['resume_bullet'], language="text")
        
        st.markdown("---")
        
        # Create tabs for Preview and Code
        out_tab1, out_tab2 = st.tabs(["Preview", "Code Source"])
        
        with out_tab1:
            st.markdown(st.session_state['readme_output'], unsafe_allow_html=True)
            
        with out_tab2:
            st.code(st.session_state['readme_output'], language="markdown", line_numbers=True)
        
        st.divider()
        st.download_button(
            label="Download README.md",
            data=st.session_state['readme_output'],
            file_name="README.md",
            mime="text/markdown"
        )

if __name__ == "__main__":
    main()
