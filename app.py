from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import requests
import io

app = Flask(__name__)
# Vercel production me secret key environment variable se leni chahiye,
# filhal hardcoded hai for simplicity.
app.secret_key = "vercel_deploy_secret_key_change_me"

# Common names for env files to search automatically
ENV_FILES = ["sample.env", ".env.example", ".env.sample", "env.example"]

def get_raw_url(repo_url, file_name):
    clean_url = repo_url.rstrip("/")
    if "github.com" in clean_url:
        parts = clean_url.split("/")
        if len(parts) >= 5:
            user = parts[3]
            repo = parts[4]
            # Try 'main' branch first
            return f"https://raw.githubusercontent.com/{user}/{repo}/main/{file_name}"
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = request.form.get('repo_url')
        if not repo_url:
             flash("Please enter a URL.")
             return redirect(url_for('index'))

        found_content = None
        
        # Step 1: Try 'main' branch
        for env_name in ENV_FILES:
            raw_url = get_raw_url(repo_url, env_name)
            if raw_url:
                try:
                    response = requests.get(raw_url, timeout=5)
                    if response.status_code == 200:
                        found_content = response.text
                        break
                except:
                    continue
        
        # Step 2: Fallback - Try 'master' branch if 'main' failed
        if not found_content:
             for env_name in ENV_FILES:
                raw_url = get_raw_url(repo_url, env_name)
                if raw_url:
                    raw_url = raw_url.replace("/main/", "/master/")
                    try:
                        response = requests.get(raw_url, timeout=5)
                        if response.status_code == 200:
                            found_content = response.text
                            break
                    except:
                        continue

        if found_content:
            # Parse keys (VAR_NAME=)
            variables = []
            lines = found_content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=')[0].strip()
                    if key:
                        variables.append(key)
            
            # Remove duplicates while keeping order
            variables = list(dict.fromkeys(variables))

            if not variables:
                 flash("File found, but no variables detected inside it.")
                 return redirect(url_for('index'))

            return render_template('index.html', variables=variables, repo_url=repo_url, step="fill_form")
        else:
            flash("Could not find any sample.env or .env.example file in this repo.")
            return redirect(url_for('index'))

    return render_template('index.html', step="input_repo")

@app.route('/download', methods=['POST'])
def download():
    env_content = ""
    # Add a header comment
    repo_url = request.form.get('repo_url', '')
    env_content += f"# Generated from: {repo_url}\n\n"

    for key, value in request.form.items():
        if key != "repo_url":
            env_content += f"{key}={value}\n"
    
    mem_file = io.BytesIO()
    mem_file.write(env_content.encode('utf-8'))
    mem_file.seek(0)
    
    return send_file(
        mem_file,
        as_attachment=True,
        download_name='.env',
        mimetype='text/plain'
    )

# Vercel doesn't need app.run(), it imports the 'app' object directly.
