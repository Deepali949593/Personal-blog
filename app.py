# File: app.py (Flask Blog with Supabase, Email, QR Login/Register)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from supabase_client import supabase
import os, json, markdown, datetime, qrcode, base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = "supersecure"

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '24mscs29@kristujayanti.com'  # change to your email
app.config['MAIL_PASSWORD'] = 'ldrlnrwertezgpei'             # use app password
mail = Mail(app)

ARTICLE_DIR = "articles"
if not os.path.exists(ARTICLE_DIR):
    os.makedirs(ARTICLE_DIR)

def load_articles():
    articles = []
    for filename in os.listdir(ARTICLE_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(ARTICLE_DIR, filename), "r") as f:
                data = json.load(f)
                data["filename"] = filename
                articles.append(data)
    return sorted(articles, key=lambda x: x["date"], reverse=True)

@app.route("/")
def index():
    q = request.args.get("q", "").lower()
    articles = load_articles()
    if q:
        articles = [a for a in articles if q in a["title"].lower() or q in " ".join(a.get("tags", [])).lower()]
    return render_template("index.html", articles=articles)

@app.route("/article/<filename>")
def article(filename):
    path = os.path.join(ARTICLE_DIR, filename)
    if not os.path.exists(path):
        return "Article not found", 404
    with open(path, "r") as f:
        data = json.load(f)
        html = markdown.markdown(data["content"])
    return render_template("article.html", title=data["title"], content=html, tags=data.get("tags", []), date=data["date"], filename=filename)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        response = supabase.table("user").select("*").eq("username", username).eq("password", password).execute()

        if response.data and len(response.data) == 1:
            user = response.data[0]
            session["logged_in"] = True
            session["username"] = username
            session["is_admin"] = user.get("is_admin", False)  # store admin status
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login_register.html")

@app.route("/admin")
def admin_panel():
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("You are not authorized to view this page.", "danger")
        return redirect(url_for("index"))

    users = supabase.table("user").select("username", "email", "is_admin").execute().data
    articles = load_articles()
    return render_template("admin_dashboard.html", users=users, articles=articles)



@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

   # ✅ Check if email already exists BEFORE anything else
    existing = supabase.table("user").select("*").eq("email", email).execute()
    if existing.data:
        flash("Email already exists, please use another.", "warning")
        return redirect(url_for("login"))

    # Generate QR Code for password
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(password)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    qr_img_io = BytesIO()
    img.save(qr_img_io, format='PNG')
    qr_img_io.seek(0)

    # Prepare welcome email
    msg = Message(f"Welcome to Peachy Blog, {username}!", sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Hello {username}!\n\nYour credentials:\nUsername: {username}\nPassword: {password}"
    msg.html = f"""
    <h2>Welcome to Peachy Blog 🍑</h2>
    <p>Hello <b>{username}</b>,</p>
    <p>Thank you for registering!</p>
    <p><b>Username:</b> {username}<br><b>Password:</b> {password}</p>
    <p>Scan this QR to store your password:</p>
    <img src="cid:qr_code_image" alt="QR Code">
    """
    msg.attach("qr.png", "image/png", qr_img_io.getvalue(), disposition='inline', headers={"Content-ID": "<qr_code_image>"})

    try:
        mail.send(msg)
    except Exception as e:
        print("Mail error:", e)
        flash("Could not send email. Please check your email config.", "danger")

    # Insert into Supabase
    supabase.table("user").insert({
        "username": username,
        "email": email,
        "password": password  # Ideally, hash before storing
    }).execute()

    flash("Registration successful! Check your email.", "success")
    return redirect(url_for("login"))



@app.route("/forgot-password")
def forgot():
    return "Password reset functionality coming soon."

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("username", None)
    return redirect(url_for("index"))

@app.route("/new", methods=["GET", "POST"])
@app.route("/edit/<filename>", methods=["GET", "POST"])
def new_article(filename=None):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    edit_mode = filename is not None
    article = {}

    if edit_mode:
        path = os.path.join(ARTICLE_DIR, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                article = json.load(f)

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        tags = [t.strip() for t in request.form["tags"].split(",") if t.strip()]
        date = article.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))

        data = {
            "title": title,
            "content": content,
            "tags": tags,
            "date": date
        }

        if edit_mode:
            with open(os.path.join(ARTICLE_DIR, filename), "w") as f:
                json.dump(data, f, indent=2)
        else:
            filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".json"
            with open(os.path.join(ARTICLE_DIR, filename), "w") as f:
                json.dump(data, f, indent=2)

        return redirect(url_for("index"))

    return render_template("new_article.html", edit_mode=edit_mode, article=article)

@app.route("/delete/<filename>")
def delete_article(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    path = os.path.join(ARTICLE_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        flash("Article deleted")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    
    
