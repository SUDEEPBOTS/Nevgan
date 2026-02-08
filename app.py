from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import requests
import io
import os

app = Flask(__name__)
# Security ke liye random key, Vercel par ye Environment Variable se leni chahiye
app.secret_key = os.urandom(24)

# In files ko dhoondne ki koshish karega
ENV_FILES = ["sample.env", ".env.example", ".env.sample", "env.example", ".env"]

def get_raw_url(repo_url, file_name, branch="main"):
    """GitHub Repo URL se Raw File URL banata hai"""
    clean_url = repo_url.rstrip("/")
    if "github.com" in clean_url:
        parts = clean_url.split("/")
        if len(parts) >= 5:
            user = parts[3]
            repo = parts[4]
            return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{file_name}"
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = request.form.get('repo_url')
        if not repo_url:
             flash("Please enter a valid GitHub URL.")
             return redirect(url_for('index'))

        found_content = None
        
        # Step 1: Pehle 'main' branch par check karo
        for env_name in ENV_FILES:
            raw_url = get_raw_url(repo_url, env_name, "main")
            if raw_url:
                try:
                    response = requests.get(raw_url, timeout=5)
                    if response.status_code == 200:
                        found_content = response.text
                        break
                except:
                    continue
        
        # Step 2: Agar 'main' fail hua, toh 'master' branch try karo
        if not found_content:
             for env_name in ENV_FILES:
                raw_url = get_raw_url(repo_url, env_name, "master")
                if raw_url:
                    try:
                        response = requests.get(raw_url, timeout=5)
                        if response.status_code == 200:
                            found_content = response.text
                            break
                    except:
                        continue

        if found_content:
            # Step 3: Variables Parse karo
            variables = []
            lines = found_content.split('\n')
            for line in lines:
                line = line.strip()
                # Comments aur empty lines ignore karo
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=')[0].strip()
                    if key:
                        variables.append(key)
            
            # Duplicates hatao (Order maintain karke)
            variables = list(dict.fromkeys(variables))

            if not variables:
                 flash("File mil gayi, par usme koi variables nahi dikhe.")
                 return redirect(url_for('index'))

            # Yahan hum 'variables' bhej rahe hain taaki HTML form bana sake
            return render_template('index.html', variables=variables, repo_url=repo_url, step="fill_form")
        else:
            flash("Is Repo mein koi sample.env file nahi mili. (Check main/master branch)")
            return redirect(url_for('index'))

    return render_template('index.html', step="input_repo")

@app.route('/download', methods=['POST'])
def download():
    """Sirf Download button dabane par ye chalega"""
    env_content = ""
    repo_url = request.form.get('repo_url', '')
    
    # Header comment
    env_content += f"# Generated from: {repo_url}\n# Created using EnvGen Tool\n\n"

    for key, value in request.form.items():
        # Repo URL aur hidden fields ko file me mat likho
        if key not in ["repo_url"]:
            env_content += f"{key}={value}\n"
    
    # File memory me banao (Disk par save karne ki zaroorat nahi)
    mem_file = io.BytesIO()
    mem_file.write(env_content.encode('utf-8'))
    mem_file.seek(0)
    
    return send_file(
        mem_file,
        as_attachment=True,
        download_name='.env',
        mimetype='text/plain'
    )

# Vercel ke liye 'app' object zaroori hai, app.run() ki zaroorat nahi hoti production me
if __name__ == '__main__':
    app.run(debug=True)
    
