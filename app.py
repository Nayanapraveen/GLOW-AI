from flask import Flask, render_template, request,redirect,url_for,session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import re
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    skin_concern = db.Column(db.String(100))

    hair_concern = db.Column(db.String(100))

    recommendations = db.Column(db.Text)
    analysis_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    brand = db.Column(db.String(100))

    category = db.Column(db.String(100))

    ingredients = db.Column(db.Text)

    skin_type = db.Column(db.String(50))

    hair_type = db.Column(db.String(50))

    warning = db.Column(db.Text)
    buy_link = db.Column(db.Text)
app.secret_key = "skincare_ai_project_secret_2026"
users={}

ingredients_db = {
    "retinol": {
        "good_for": ["aging"],
        "avoid_with": ["vitamin_c", "salicylic_acid"]
    },
    "vitamin_c": {
        "good_for": ["pigmentation"],
        "avoid_with": ["retinol"]
    },
    "salicylic_acid": {
        "good_for": ["acne"],
        "avoid_with": ["retinol"]
    },
    "niacinamide": {
        "good_for": ["acne", "oily"],
        "avoid_with": []
    }
}

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters long."
            )

        if not re.search(r"[A-Z]", password):
            return render_template(
                "register.html",
                error="Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", password):
            return render_template(
                "register.html",
                error="Password must contain at least one lowercase letter."
            )

        if not re.search(r"[0-9]", password):
            return render_template(
                "register.html",
                error="Password must contain at least one number."
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return render_template(
                "register.html",
                error="Password must contain at least one special character."
            )
        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match!"
            )


        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')


        new_user = User(username=username, password=hashed_password,role="user")

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login", success="Registration completed successfully!"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user'] = user.username
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("dashboard"))

    success = request.args.get("success")
    return render_template("login.html", success=success)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form["username"]
        new_password = request.form["new_password"]

        user = User.query.filter_by(username=username).first()

        if user:
            hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
            user.password = hashed_password
            db.session.commit()
            return redirect(url_for("login"))
        else:
            return "User not found"

    return render_template("forgot_password.html")

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for("login"))

@app.route("/recommend", methods=["POST"])
def recommend():
    if "user" not in session:
        return redirect(url_for("login"))

    skin_concern = request.form["skin_concern"]
    hair_concern = request.form["hair_concern"]
    current_ingredients = request.form["current_ingredients"].lower().split(",")

    ingredients_db = {
        "salicylic acid": {"type": "skin", "concerns": ["acne"], "avoid_with": ["retinol"]},
        "retinol": {"type": "skin", "concerns": ["aging"], "avoid_with": ["salicylic acid"]},
        "vitamin c": {"type": "skin", "concerns": ["pigmentation"], "avoid_with": ["retinol"]},
        "hyaluronic acid": {"type": "skin", "concerns": ["dryness"], "avoid_with": []},

        "ketoconazole": {"type": "hair", "concerns": ["dandruff"], "avoid_with": []},
        "biotin": {"type": "hair", "concerns": ["hairfall"], "avoid_with": []},
        "argan oil": {"type": "hair", "concerns": ["frizz"], "avoid_with": []}
    }

    skin_recommendations = []
    hair_recommendations = []
    warnings = []


    for ingredient, data in ingredients_db.items():
        if skin_concern in data["concerns"] and data["type"] == "skin":
            skin_recommendations.append(ingredient)

        if hair_concern in data["concerns"] and data["type"] == "hair":
            hair_recommendations.append(ingredient)


    for ing in current_ingredients:
        ing = ing.strip()
        if ing in ingredients_db:
            for avoid in ingredients_db[ing]["avoid_with"]:
                if avoid in current_ingredients:
                    warnings.append(f"{ing} should not be used with {avoid}")


    current_user = User.query.filter_by(username=session["user"]).first()

    if not current_user:
        return "User not found"

    all_recommendations = (
        "Skin: " + ", ".join(skin_recommendations) +
        " | Hair: " + ", ".join(hair_recommendations) +
        " | Warnings: " + ", ".join(warnings)
    )


    if skin_concern:
        analysis_type = "skin"
    elif hair_concern:
        analysis_type = "hair"
    else:
        analysis_type = "unknown"

    analysis = Analysis(
        user_id=current_user.id,
        skin_concern=skin_concern,
        hair_concern=hair_concern,
        recommendations=all_recommendations,
        analysis_type=analysis_type
    )

    db.session.add(analysis)
    db.session.commit()

    return render_template(
        "result.html",
        skin_recommendations=skin_recommendations,
        hair_recommendations=hair_recommendations,
        warnings=warnings
    )
@app.route("/skin_history")
def skin_history():
    if "user" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session['user']).first()

    history = Analysis.query.filter_by(
        user_id=user.id,
        analysis_type="skin"
    ).all()

    return render_template("history.html", history=history, type="skin")
@app.route("/hair_history")
def hair_history():
    if "user" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session['user']).first()

    history = Analysis.query.filter_by(
        user_id=user.id,
        analysis_type="hair"
    ).all()

    return render_template("history.html", history=history, type="hair")
@app.route('/skin', methods=['GET', 'POST'])
def skin():
    print("SKIN ROUTE HIT")
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':

        skin_type = request.form['skin_type']
        skin_concern = request.form['skin_concern']


        skin_ingredients = []
        if skin_type == "oily skin":
            skin_ingredients += ["salicylic acid", "niacinamide", "tea tree"]

        elif skin_type == "dry skin":
            skin_ingredients += ["hyaluronic acid", "ceramides", "glycerin"]

        elif skin_type == "combination skin":
            skin_ingredients += ["niacinamide", "hyaluronic acid"]

        elif skin_type == "sensitive skin":
            skin_ingredients += ["aloe vera", "chamomile"]

        if skin_concern == "acne":
            skin_ingredients += [ "salicylic acid", "niacinamide","tea tree","benzoyl peroxide" "zinc"]


        elif skin_concern == "pigmentation":
            skin_ingredients += [ "vitamin c","niacinamide","alpha arbutin", "kojic acid", "glycolic acid"]


        elif skin_concern == "aging":
            skin_ingredients += ["retinol","peptides","vitamin c","hyaluronic acid","collagen"]

        else:
            skin_ingredients = []


        skin_products = []
        if skin_type == "oily skin":
            skin_products += [
                {"name": "The Ordinary Niacinamide 10% + Zinc", "desc": "Controls oil & acne", "link": "https://www.nykaa.com/the-ordinary-niacinamide-10percent-zinc-1percent/p/15707745?skuId=5003164","image": "https://images-static.nykaa.com/media/catalog/product/8/8/88a48a1THECI00000026_2.jpg?tr=w-344,h-344,cm-pad_resize","ingredients": ["niacinamide"]},
                {"name": "Minimalist Salicylic Acid Serum", "desc": "Unclogs pores", "link": "https://beminimalist.co/products/niacinamide-10-with-matmarine?variant=45154956705953","image": "https://sfycdn.speedsize.com/56385b25-4e17-4a9a-9bec-c421c18686fb/beminimalist.co/cdn/shop/files/Nia10New.png?crop=center&height=1260&v=1721398127&width=840","ingredients": ["salicylic acid"]},
                {"name": "Plum green tea pore cleansing facewash", "desc": "Fights acne naturally", "link": "https://plumgoodness.com/products/green-tea-pore-cleansing-face-wash?variant=43770031079484","image": "https://plumgoodness.com/cdn/shop/files/02_f7ea497e-9986-4b8a-a638-513aa10cad18.jpg?v=1771581308&width=800","ingredients": ["greentea","salicylic acid"]},
                {"name": "Mama earth Tea Tree moisturizer", "desc": "Budget acne care", "link": "https://mamaearth.in/product/tea-tree-oil-free-face-moisturizer-with-tea-tree-salicylic-acid-for-acne-pimples-80-ml?srsltid=AfmBOopPdM-2InkSIH7EU7_U2TtNwdWJH_D-ZXTgPOv1ubNJK7h-S1Zg","image": "https://images.mamaearth.in/catalog/product/t/e/tea-tree-oil-moisturizer-with-box-_-ingredients.jpg?format=auto&height=600","ingredients": ["tea tree","salicylic acid"]},
                {"name": "Dot & Key Niacinamide Serum", "desc": "Balances oil", "link": "https://share.google/y36KaPZnL5ZSYwGTp","image": "https://m.media-amazon.com/images/I/51EpZT48XJL._SX522_.jpg","ingredients": ["niacinamide"]}
            ]

        elif skin_type == "dry skin":
            skin_products += [
                {"name": "L'Oréal Hyaluronic Acid Serum", "desc": "Deep hydration", "link": "https://www.nykaa.com/l-oreal-paris-revitalift-1-5-hyaluronic-acid-serum/p/1112060?skuId=1112054","image": "https://m.media-amazon.com/images/I/51dyKxcQAaL._SX522_.jpg","ingredients": ["hyaluronic acid"]},
                {"name": "Minimalist Hyaluronic Acid 2%", "desc": "Lightweight hydration", "link": "https://share.google/b7KdxFPYspFzSpasN","image": "https://sfycdn.speedsize.com/56385b25-4e17-4a9a-9bec-c421c18686fb/beminimalist.co/cdn/shop/products/HAPGA2_1200-1-min.png?crop=center&height=1260&v=1646395962&width=840","ingredients": ["hyaluronic acid"]},
                {"name": "Neutrogena Hydro Boost", "desc": "Locks moisture", "link": "https://share.google/SPTJidCoYBDqIbN58","image": "https://m.media-amazon.com/images/I/51ggE7KJd8L._SX522_.jpg","ingredients": ["hyaluronic acid","glycerin"]},
                {"name": "Ceta phil Moisturizing Cream", "desc": "Best for sensitive dry skin", "link": "https://share.google/EsOjp565VYtaSHvYl","image": "https://images-static.nykaa.com/media/catalog/product/8/1/8142f51NYCETA0000003_1.jpg?tr=w-344,h-344,cm-pad_resize","ingredients": ["glycerin","ceramides"]},
                {"name": "Dot & Key Ceramide Moisturizer", "desc": "Repairs skin barrier", "link": "https://share.google/B3hhZhKkMCZlnz60E","image": "https://m.media-amazon.com/images/I/41BjnnbhTnL._SY300_SX300_QL70_FMwebp_.jpg","ingredients": ["ceramides"]}
            ]

        elif skin_type == "combination skin":
            skin_products += [
                {"name": "Minimalist Niacinamide Serum", "desc": "Balances oil & dryness", "link": "https://share.google/ecZCDiCbouBMQ25Qr","image": "https://m.media-amazon.com/images/I/61MSZ7e7NmL._SX522_.jpg","ingredients": ["niacinamide"]},
                {"name": "DermDoc kojic acid and niacinamide", "desc": "targets darkspot and eneven skintone", "link": "https://share.google/zvNd9Wh3dBVFGzjoZ","image": "https://buydermdoc.com/cdn/shop/files/dermdoc-2-percentage-kojic-acid-face-serum-20-ml_3_display_1772623467_db930704.jpg?v=1775038220&width=823","ingredients": ["kojic acid","niacinamide"]},
                {"name": "Plum green tea pore cleansing facewash", "desc": "Controls T-zone oil", "link": "https://plumgoodness.com/products/green-tea-pore-cleansing-face-wash?variant=43770031079484","image": "https://plumgoodness.com/cdn/shop/files/01_56929db7-8603-4976-b8c8-c8a1b7eaaa5a.jpg?v=1771581308&width=800","ingredients": ["green tea","salicylic acid"]},
                {"name": "Mama earth Tea Tree moisturize", "desc": "Light hydration", "link": "https://mamaearth.in/product/tea-tree-oil-free-face-moisturizer-with-tea-tree-salicylic-acid-for-acne-pimples-80-ml?srsltid=AfmBOopPdM-2InkSIH7EU7_U2TtNwdWJH_D-ZXTgPOv1ubNJK7h-S1Zg","image": "https://images.mamaearth.in/catalog/product/t/e/tea-tree-oil-moisturizer-with-box-_-ingredients.jpg?format=auto&height=600","ingredients": ["tea tree","salicyclic acid"]},
                {"name": "Dot & Key Balancing Serum", "desc": "Maintains skin balance", "link": "https://share.google/Mp7LYu9KMLcD83IEt","image": "https://m.media-amazon.com/images/I/61prDjmR7-L._SX522_.jpg","ingredients": ["niacinamide"]},
            ]

        elif skin_type == "sensitive skin":
            skin_products += [
                {"name": "Aloe Vera Gel (Wow Skin Science)", "desc": "Soothes irritation", "link": "https://share.google/mB0hkBwIvqMokhx9n","image": "https://m.media-amazon.com/images/I/517Xe-WpnsL._SX522_.jpg","ingredients": ["aloe vera"]},
                {"name": "Cetaphil Gentle Cleanser", "desc": "Very mild & safe", "link": "https://share.google/3923L5HD9OcvaVFwT","image": "https://m.media-amazon.com/images/I/61Ti2uv6V3L._SX522_.jpg","ingredients": ["glycerine"]},
                {"name": "Bioderma Sensibio Cream", "desc": "Premium sensitive care", "link": "https://share.google/34SNovnQEybsNlXk5","image": "https://images-static.nykaa.com/media/catalog/product/6/8/688e0c7BIODE00000063_1.jpg?tr=w-344,h-344,cm-pad_resize","ingredients": ["ceramides"]},
                {"name": "Mamaearth Aloe Vera Gel", "desc": "Budget soothing option", "link": "https://share.google/8M6GnOXsPOBXcwBjY","image": "https://m.media-amazon.com/images/I/51WJeRNyB7L._SX522_.jpg","ingredients": ["aloe vera"]},
                {"name": "Dot & Key Cica Gel", "desc": "Calms redness", "link": "https://share.google/1EBUrYmKkbK62XCwh","image": "https://www.dotandkey.com/cdn/shop/files/1_633a965b-708a-484e-a47b-047cefe8d398.jpg?v=1754919028&width=700","ingredients": ["cica"]}
            ]
        if skin_concern == "acne":
          skin_products += [
        {"name": "Minimalist 2% Salicylic Acid Serum", "desc": "Budget-friendly, best for acne", "link": "https://beminimalist.co/products/niacinamide-10-with-matmarine?variant=45154956705953","image": "https://sfycdn.speedsize.com/56385b25-4e17-4a9a-9bec-c421c18686fb/beminimalist.co/cdn/shop/files/Nia10New.png?crop=center&height=1260&v=1721398127&width=840","ingredients": ["salicylic acid"]},
        {"name": "The Ordinary Salicylic Acid 2%", "desc": "Highly rated global product", "link": "https://share.google/K6Tqdz2r2JRN9mOrI","image": "https://images-static.nykaa.com/media/catalog/product/8/8/88a48a1THECI00000015_1.jpg?tr=w-344,h-344,cm-pad_resize","ingredients": ["salicylic acid"]},
        {"name": "Plum 10% Niacinamide Serum", "desc": "Controls oil & breakouts", "link": "https://share.google/uQiWX2NIJFPt3vJNb","image": "https://plumgoodness.com/cdn/shop/files/01_Moodshot_Texture_Copy_15ml.jpg?v=1773214029&width=800","ingredients": ["niacinamide"]},
        {"name": "Mamaearth Tea Tree Serum", "desc": "Natural acne control", "link": "https://share.google/MaFNwW2sq05IoVrHy","image": "https://images.mamaearth.in/catalog/product/_/t/_tea-tree-face-serum_.jpg?format=auto&height=600","ingredients": ["tea tree"]},
        {"name": "Foxtale Oil-Free Acne Wash", "desc": "Calm skin in 3 days", "link": "https://share.google/UDlLVs1WdZms1zEUO","image": "https://m.media-amazon.com/images/I/51CZlms5CEL._SX522_.jpg","ingredients": ["salicylic acid"]}
    ]


        elif skin_concern == "pigmentation":
          skin_products += [
        {"name": "Minimalist Vitamin C 10%", "desc": "Best budget brightening serum", "link": "https://share.google/CQ1yeQGt4eeStrRIE","image": "https://sfycdn.speedsize.com/56385b25-4e17-4a9a-9bec-c421c18686fb/beminimalist.co/cdn/shop/products/VitaminC10_1200-1-min.png?crop=center&height=1260&v=1646543848&width=840","ingredients": ["vitamin C"]},
        {"name": "Plum Vitamin C Serum", "desc": "Good for dark spots", "link": "https://share.google/Q1MiXHwINg86Ie1tc","image": "https://plumgoodness.com/cdn/shop/files/01_17417c95-3437-4680-b7d0-fbc206f840bc.jpg?v=1732258398&width=800","ingredients": ["vitamin C"]},
        {"name": "The Derma Co 2% Alpha Arbutin", "desc": "Targets pigmentation", "link": "https://share.google/ZRZJ2s9v448QoZ4ka","image": "https://thedermaco.com/cdn/shop/files/2__alpha_arbutin_colored_bg.jpg?v=1758286539&width=713","ingredients": ["alpha arbutin"]},
        {"name": "Mamaearth Vitamin C Serum", "desc": "Popular and affordable", "link": "https://share.google/tBU0Bvy64r5ylTI54","image": "https://images.mamaearth.in/catalog/product/v/i/vitamin-c-glow-serum_1_1_1.jpg?format=auto&height=600","ingredients": ["vitamin C"]},
        {"name": "DermDoc 2% kojic acid serum", "desc": "Dark spots and pigmentation control", "link": "https://share.google/fWAH3T7R7iW3EAX3I","image": "https://media6.ppl-media.com/tr:h-750,w-750,c-at_max,dpr-2,q-40,f-avif/static/img/product/401229/dermdoc-2-percentage-kojic-acid-face-serum-20-ml_1_display_1772623465_c6c94fe3.jpg","ingredients": ["kojic acid"]}
    ]

        elif skin_concern == "aging":
           skin_products += [
        {"name": "Minimalist Retinol 0.3%", "desc": "Best beginner retinol", "link": "https://share.google/rRJHco7XFyd5ca9S4","image": "https://sfycdn.speedsize.com/56385b25-4e17-4a9a-9bec-c421c18686fb/beminimalist.co/cdn/shop/files/Reti3New.png?crop=center&height=1260&v=1721398129&width=840","ingredients": ["retinol"]},
        {"name": "Olay Regenerist Cream", "desc": "Top anti-aging moisturizer", "link": "https://share.google/JKTBg1r6T6x9h3HhV","image": "https://m.media-amazon.com/images/I/51qg80PZR6L._SX522_.jpg","ingredients": ["peptides"]},
        {"name": "L'Oréal Revitalift Serum", "desc": "Reduces wrinkles & fine lines", "link": "https://amzn.in/d/0ccFSzGJ","image": "https://m.media-amazon.com/images/I/51dyKxcQAaL._SX522_.jpg","ingredients": ["hyaluronic acid"]},
        {"name": "Garnier skin naturals", "desc": "Anti ageing cream", "link": "https://amzn.in/d/0b1VdL5I","image": "https://m.media-amazon.com/images/I/51FTaE92esL._SX522_.jpg","ingredients": ["vitamin C"]},
        {"name": "Mamaearth Retinol Serum", "desc": "Affordable anti-aging option", "link": "https://share.google/StzzUGXBm0p45UlO1","image": "https://cdn.tirabeauty.com/v2/billowing-snowflake-434234/tira-p/wrkr/products/pictures/item/free/resize-w:1080/mamaearth/1005362/0/7gtqRuJL9--tgV46s83N0-1.jpg","ingredients": ["retinol"]}
    ]



        if not skin_products:

            skin_products = [
                {"name": "Cetaphil Cleanser", "desc": "Suitable for all skin types", "link": "https://share.google/3923L5HD9OcvaVFwT","image": "https://m.media-amazon.com/images/I/61Ti2uv6V3L._SX522_.jpg"},
                {"name": "Neutrogena Moisturizer", "desc": "Daily hydration", "link": "https://share.google/SPTJidCoYBDqIbN58","image": "https://m.media-amazon.com/images/I/51ggE7KJd8L._SX522_.jpg"},
                {"name": "Minimalist Sunscreen SPF 50", "desc": "Essential sun protection", "link": "https://share.google/DWiFSXsYQIhPEEYVu","image": "https://m.media-amazon.com/images/I/61tvX-QQDhL._SX522_.jpg"},
                {"name": "Plum Green Tea Face Wash", "desc": "Gentle cleansing", "link": "https://share.google/4uGJCLda1VwGGpFqu","image": "https://plumgoodness.com/cdn/shop/files/01_56929db7-8603-4976-b8c8-c8a1b7eaaa5a.jpg?v=1771581308&width=800"},
                {"name": "Mamaearth Daily Glow Cream", "desc": "Basic skincare routine", "link": "https://share.google/0BLzdI6AyGGOkwN9F","image": "https://m.media-amazon.com/images/I/51H1dx3ULHL._SX679_.jpg"}
            ]


        user = User.query.filter_by(username=session['user']).first()
        print("User: ", user)
        print("Saving analysis....")

        if not user:
            return "User not found. Please login again."

        new_analysis = Analysis(
            user_id=user.id,
            skin_concern=skin_concern,
            hair_concern=None,
            recommendations=f"Skin: {skin_type}, Concern: {skin_concern}",
            analysis_type="skin"
        )

        db.session.add(new_analysis)
        db.session.commit()
        print("SAVED TO DB")

        return render_template(
            "result.html",
            skin_type=skin_type,
            skin_concern=skin_concern,
            skin_ingredients=skin_ingredients,
            skin_products=skin_products,
            hair_ingredients=[],
            hair_products=[]
        )

    return render_template("skin.html")
@app.route('/hair', methods=['GET', 'POST'])
def hair():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':

        hair_type = request.form['hair_type']
        hair_concern = request.form['hair_concern']

        if hair_type == "curly":
            hair_type_rec = ["shea butter", "curl cream"]
        elif hair_type == "straight":
            hair_type_rec = ["keratin", "serum"]
        else:
            hair_type_rec = ["basic care"]

        if hair_concern == "hairfall":
            hair_concern_rec = ["biotin", "castor oil"]
        elif hair_concern == "dandruff":
            hair_concern_rec = ["tea tree oil"]
        elif hair_concern == "dry":
            hair_concern_rec = ["coconut oil"]
        elif hair_concern == "frizzy":
            hair_concern_rec = ["argan oil"]
        else:
            hair_concern_rec = ["general care"]

        hair_ingredients = hair_type_rec + hair_concern_rec


        hair_products = []
        if hair_type == "curly":
            hair_products += [
                {"name": "Arata Curl Defining Cream", "desc": "Defines curls & reduces frizz", "link": "https://amzn.in/d/0h54ZHlm","image": "https://m.media-amazon.com/images/I/51MKJz4lQgL._SX522_PIbundle-2,TopRight,0,0_AA522SH20_.jpg","ingredients": ["argan oil","shea butter"]},
                {"name": "Fix My Curls Curl Cream and Defining gel", "desc": "Hydrates curls", "link": "https://share.google/i9OTxKtfO6S9od7KK","image": "https://m.media-amazon.com/images/I/61cQOUWUnlL._SX522_PIbundle-2,TopRight,0,0_AA522SH20_.jpg","ingredients": ["shea butter","flaxseed"]},
                {"name": "Bare anatomy curl Boosting cream leave in conditioner", "desc": "smoother,Healthy & glossy hair", "link": "https://share.google/ZgDE1R2RmxpQ0pMd0","image": "https://m.media-amazon.com/images/I/411OEENZ9SL._SY300_SX300_QL70_FMwebp_.jpg","ingredients": ["keratin","argan oil"]},
                {"name": "Ashba Botanics Curl Cream", "desc": "Premium curls", "link": "https://share.google/Ffz0rlXym3Gho9EX6","image": "https://m.media-amazon.com/images/I/61gjEhoii-L._SX522_.jpg","ingredients": ["aloe vera","shea butter"]},
                {"name": "Moxie Beauty", "desc": "super defining", "link": "https://share.google/lYLQ3RrWhIo65cDBh","image": "https://m.media-amazon.com/images/I/31DXnr+ReLL._SY300_SX300_QL70_FMwebp_.jpg","ingredients": ["argan oil"]}
            ]

        elif hair_type == "straight":
            hair_products += [
                {"name": "Streax Hair Serum", "desc": "Smooth & shiny hair", "link": "https://share.google/jdVaaB9CPDavTsgfp","image": "https://m.media-amazon.com/images/I/51wjgvU58tL._SX522_PIbundle-3,TopRight,0,0_AA522SH20_.jpg","ingredients": ["silicones"]},
                {"name": "Livon Hair Serum", "desc": "Frizz control", "link": "https://share.google/hazlhS3R70WuZZDtI","image": "https://mylivonmysalon.com/_next/image?url=https%3A%2F%2Fassets.mylivonmysalon.com%2Fhair-serum%2Fgo-frizz-free-pdp-hero-banner-new.webp&w=828&q=75","ingredients": ["silicones"]},
                {"name": "L'Oréal Oil Serum", "desc": "Premium shine", "link": "https://share.google/LbWxMya8xB1EQqUNE","image": "https://www.lorealparis.co.in/-/media/project/loreal/brand-sites/oap/apac/in/products/hair/hair-care/extraordinary-oil/serum/exoil-serum.png","ingredients": ["arganoil","silicones"]},
                {"name": "Matrix Biolage Serum", "desc": "Professional finish", "link": "https://share.google/sItkHTyCx2b2uHtxK","image": "https://m.media-amazon.com/images/I/51PBDFlTFKL._SX522_.jpg","ingredients": ["silicones"]},
                {"name": "Tresemme Keratin Serum", "desc": "Smoothening care", "link": "https://share.google/11lDOBuB6o4wHw3iu","image": "https://www.tresemme.in/cdn/shop/files/26401_S1_8901030928598_5d8a3bc8-2012-4792-a2ad-042ab05984e2.jpg?v=1692854685&width=500","ingredients": ["keratin","silicones"]},
            ]


        if hair_concern == "hairfall":
            hair_products += [
                {"name": "WOW Onion Oil", "desc": "Reduces hair fall", "link": "https://share.google/CarA0i7yfPbsXdHpA","image": "https://media.buywow.in/public/80a36754-4fdc-40b6-912a-01b8187074be","ingredients": ["onion oil"]},
                {"name": "Alps Goodness Rosemary water", "desc": "Hair growth Expert", "link": "https://share.google/GeRktmgT6XaQ0nyDJ","image": "https://media6.ppl-media.com/tr:h-750,w-750,c-at_max,dpr-2,q-40,f-avif/static/img/product/403651/alps-goodness-rosemary-water-100-ml-rosemary-water-for-hair-hair-spray-for-hair-growth-1_1_display_1773724780_0d2f50c9.jpg","ingredients": ["rosemary"]},
                {"name": "Indulekha Bringha Oil", "desc": "Clinically proven", "link": "https://share.google/TG3UpzfYPjEjqZ0X4","image": "https://m.media-amazon.com/images/I/61IxF1ljJHL._SX522_.jpg","ingredients": ["bhringraj"]},
                {"name": "Khadi Herbal Shampoo", "desc": "Natural care", "link": "https://share.google/HnH4z9XN9QjvlVZhc", "image": "https://m.media-amazon.com/images/I/61vWAbbZjVL._SX522_.jpg","ingredients": ["amla","shikakai"]},
                {"name": "Biotin Hair Serum", "desc": "Strengthens roots", "link": "https://share.google/WGu20WAp5SXSQQR1Q","image": "https://rukminim2.flixcart.com/image/1536/1536/xif0q/hair-serum/u/m/p/50-biotin-hair-serum-men-women-volamena-original-imagugzhccebhbx4.jpeg?q=90","ingredients": ["biotin"]},
            ]

        elif hair_concern == "dandruff":
            hair_products += [
                {"name": "Head & Shoulders", "desc": "Removes dandruff", "link": "https://amzn.in/d/0fcwJYDO","image": "https://m.media-amazon.com/images/I/51cKRFpX-RL._SX522_.jpg","ingredients": ["zinc pyrithione"]},
                {"name": "Pilgrim Tea Tree Shampoo", "desc": "Non Drying Anti dandruff", "link": "https://share.google/RdZy6ZnTj7axa4y5h","image": "https://discoverpilgrim.com/cdn/shop/files/1.2_White_background_stamp.jpg?v=1761921840&width=800","ingredients": ["tea tree"]},
                {"name": "Mamaearth Tea Tree Shampoo", "desc": "Gentle care", "link": "https://share.google/mRE4IkxQSgoEuXjhH","image": "https://images.mamaearth.in/catalog/product/t/e/tea_tree_shampoo_1.jpg?format=auto&height=600","ingredients": ["tea tree"]},
                {"name": "Biotique Neem Shampoo", "desc": "Ayurvedic", "link": "https://share.google/dzdeK2PiZPxc3FiEq","image": "https://m.media-amazon.com/images/I/618zSs5JZfL._SX522_.jpg","ingredients": ["neem"]},
                {"name": "Scalpe Pro", "desc": "Strong treatment", "link": "https://share.google/x4vhnOQMEuWjNS2lK","image": "https://m.media-amazon.com/images/I/61LXLrSGo2L._SX522_.jpg","ingredients": ["ketoconazole"]},
            ]

        elif hair_concern == "dry":
            hair_products += [
                {"name": "Parachute Coconut Oil", "desc": "Deep nourishment", "link": "https://share.google/zoCfJFfU213b0hbKx","image": "https://m.media-amazon.com/images/I/61qkszG588L._SX522_.jpg","ingredients": ["coconut oil"]},
                {"name": "WOW Coconut Shampoo", "desc": "Hydration", "link": "https://share.google/M06TagLq3VV7XvjjH","image": "https://m.media-amazon.com/images/I/61buXAWMptL._SX522_.jpg","ingredients": ["coconut oil"]},
                {"name": "Dove Repair Shampoo", "desc": "Dry hair repair", "link": "https://share.google/En78sWIvQkGCqK1a2","image": "https://m.media-amazon.com/images/I/41KgBKSbLqL._SX522_.jpg","ingredients": ["keratin"]},
                {"name": "Tresemme Hair Mask", "desc": "Deep conditioning", "link": "https://share.google/yYWQhsrZ0iswV3vQl","image": "https://m.media-amazon.com/images/I/51+Td55XX7L._SX522_.jpg","ingredients": ["keratin","argan oil"]},
                {"name": "Love beauty and planet shampoo", "desc": "Sulphate free smooth and serene", "link": "https://share.google/G60isgUvMAtNYSxgY","image": "https://m.media-amazon.com/images/I/51JJW42462L._SX679_.jpg","ingredients": ["coconut oil"]},
            ]

        elif hair_concern == "frizzy":
            hair_products += [
                {"name": "Livon Anti-Frizz", "desc": "Instant smoothness", "link": "https://share.google/hazlhS3R70WuZZDtI","image": "https://mylivonmysalon.com/_next/image?url=https%3A%2F%2Fassets.mylivonmysalon.com%2Fhair-serum%2Fgo-frizz-free-pdp-hero-banner-new.webp&w=828&q=75","ingredients": ["silicones"]},
                {"name": "Streax Walnut Serum", "desc": "Smoothens hair", "link": "https://share.google/jdVaaB9CPDavTsgfp","image": "https://m.media-amazon.com/images/I/51wjgvU58tL._SX522_PIbundle-3,TopRight,0,0_AA522SH20_.jpg","ingredients": ["silicones","walnut oil"]},
                {"name": "L'Oréal Smooth Serum", "desc": "Humidity control", "link": "https://share.google/LbWxMya8xB1EQqUNE","image": "https://www.lorealparis.co.in/-/media/project/loreal/brand-sites/oap/apac/in/products/hair/hair-care/extraordinary-oil/serum/exoil-serum.png","ingredients": ["argan oil","silicones"]},
                {"name": "Matrix Smoothproof", "desc": "Professional care", "link": "https://share.google/sItkHTyCx2b2uHtxK","image": "https://m.media-amazon.com/images/I/51PBDFlTFKL._SX522_.jpg","ingredients": ["silicones"]},
                {"name": "Tresemme Conditioner", "desc": "Silky finish", "link": "https://share.google/OaIKLn2wKTX1GIFIZ","image": "https://m.media-amazon.com/images/I/41ExLtOFuKL._SX522_.jpg","ingredients": ["keratin"]},
            ]

        if not hair_products:
            hair_products = [
                {"name": "Dove Daily Shampoo", "desc": "Everyday care", "link": "https://amzn.in/d/08fowayw","image": "https://m.media-amazon.com/images/I/41we053wXbL._SX522_.jpg"},
                {"name": "Clinic Plus", "desc": "Budget option", "link": "https://amzn.in/d/0fTmN49w","image": "https://m.media-amazon.com/images/I/51yMChYQpBL._SX522_.jpg"},
                {"name": "Pantene Advanced", "desc": "Strong hair", "link": "https://amzn.in/d/0iIenmC6","image": "https://m.media-amazon.com/images/I/51ulx+9juZL._SX522_.jpg"},
                {"name": "Tresemme Daily", "desc": "Salon feel", "link": "https://amzn.in/d/08dZkCY8","image": "https://m.media-amazon.com/images/I/5146VnEc9dL._SX522_.jpg"},
                {"name": "Sunsilk Black", "desc": "Shiny hair", "link": "https://amzn.in/d/0bbUXJnc","image": "https://m.media-amazon.com/images/I/5146VnEc9dL._SX522_.jpg"},
            ]


        user = User.query.filter_by(username=session['user']).first()
        print("User: ", user)
        print("Saving analysis....")
        if not user:
            return "User not found. Please login again."

        new_analysis = Analysis(
            user_id=user.id,
            skin_concern=None,
            hair_concern=hair_concern,
            recommendations=f"Hair: {hair_type}, Concern: {hair_concern}",
            analysis_type="hair"
        )

        db.session.add(new_analysis)
        db.session.commit()

        return render_template(
            "result.html",
            hair_type=hair_type,
            hair_concern=hair_concern,
            hair_ingredients=hair_ingredients,
            hair_products=hair_products,
            skin_ingredients=[],   # hide skin
            skin_products=[]
        )

    return render_template("hair.html")
@app.route("/admin")
def admin_dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    current_user = User.query.filter_by(username=session["user"]).first()

    if current_user.role != "admin":
        return "Access Denied"

    users = User.query.all()
    analyses = Analysis.query.all()

    return render_template("admin_dashboard.html", users=users, analyses=analyses)
with app.app_context():
    db.create_all()
@app.route("/delete_user/<int:id>")
def delete_user(id):

    if "user" not in session:
        return redirect(url_for("login"))

    current_user = User.query.filter_by(username=session["user"]).first()

    if current_user.role != "admin":
        return "Access Denied"

    user = User.query.get(id)

    if user:
        db.session.delete(user)
        db.session.commit()

    return redirect("/admin")
@app.route("/delete_analysis/<int:id>")
def delete_analysis(id):
    if "user" not in session:
        return redirect(url_for("login"))

    current_user = User.query.filter_by(username=session["user"]).first()

    if current_user.role != "admin":
        return "Access Denied"

    analysis = Analysis.query.get(id)

    if analysis:
        db.session.delete(analysis)
        db.session.commit()

    return redirect("/admin")
@app.route("/make_admin/<int:id>")
def make_admin(id):


    if "user" not in session:
        return redirect(url_for("login"))

    current_user = User.query.filter_by(username=session["user"]).first()

    if current_user.role != "admin":
       return "Access Denied"

    user = User.query.get(id)

    if user:
        user.role = "admin"
        db.session.commit()

    return redirect("/admin")
@app.route("/chatbot", methods=["POST"])
def chatbot():

    user_msg = request.form["message"].lower()

    if any(word in user_msg for word in ["hi", "hello", "hey"]):
        return "Hey! 😊 Ask me anything about skin or hair!"

    if "acne" in user_msg:
        return "Acne? Try salicylic acid and keep your skin clean."

    elif "oily skin" in user_msg:
        return "Use oil-free cleanser and lightweight moisturizer."

    elif "dry skin" in user_msg:
        return "Use hydrating ingredients like hyaluronic acid."

    elif "pigmentation" in user_msg:
        return "Vitamin C and sunscreen help reduce pigmentation."

    elif "ageing" in user_msg or "wrinkles" in user_msg:
        return  "Use retinol, vitamin C, and sunscreen for anti-aging."

    elif "routine" in user_msg:
        return "Morning: Cleanser → Moisturizer → Sunscreen\nNight: Cleanser → Treatment → Moisturizer"

    elif "hair fall" in user_msg:
        return "Use biotin, onion oil, and reduce stress."

    elif "dandruff" in user_msg:
        return "Use anti-dandruff shampoo with tea tree."

    elif "dry hair" in user_msg:
        return "Use conditioner, oiling, and hair masks."

    elif "frizz" in user_msg:
        return "Use anti-frizz serum or argan oil."

    elif "which page" in user_msg:
        return "Use Skin Analysis for skin issues and Hair Analysis for hair issues."

    else:
        return "I can help with skincare, haircare, routines, and ingredients 😊"
@app.route("/skin_quiz", methods=["GET", "POST"])
def skin_quiz():

    if request.method == "POST":

        oily_score = 0
        dry_score = 0
        normal_score = 0
        sensitive_score = 0

        for i in range(1, 11):

            ans = request.form.get(f"q{i}")

            if ans == "oily":
                oily_score += 1

            elif ans == "dry":
                dry_score += 1

            elif ans == "normal":
                normal_score += 1

            elif ans == "sensitive":
                sensitive_score += 1

        if sensitive_score >= 2:
            skin_type = "Sensitive Skin"

        elif oily_score >= dry_score and oily_score >= normal_score:
            skin_type = "Oily Skin"

        elif dry_score >= oily_score and dry_score >= normal_score:
            skin_type = "Dry Skin"

        else:
            skin_type = "Combination Skin"

        return render_template(
            "quiz_result.html",
            skin_type=skin_type
        )

    return render_template("skin_quiz.html")
@app.route("/hair_quiz", methods=["GET", "POST"])
def hair_quiz():

    if request.method == "POST":

        oily_score = 0
        dry_score = 0
        normal_score = 0
        damaged_score = 0

        for i in range(1, 11):

            ans = request.form.get(f"q{i}")

            if ans == "oily":
                oily_score += 1

            elif ans == "dry":
                dry_score += 1

            elif ans == "normal":
                normal_score += 1

            elif ans == "damaged":
                damaged_score += 1

        if damaged_score >= 2:
            hair_type = "Damaged Hair"

        elif oily_score >= dry_score and oily_score >= normal_score:
            hair_type = "Oily Hair"

        elif dry_score >= oily_score and dry_score >= normal_score:
            hair_type = "Dry Hair"

        else:
            hair_type = "Normal Hair"

        return render_template(
            "quiz_result.html",
            hair_type=hair_type
        )

    return render_template("hair_quiz.html")
@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():

    if request.method == 'POST':

        product = Product(

            name=request.form['name'],

            brand=request.form['brand'],

            category=request.form['category'],

            skin_type=request.form['skin_type'],

            hair_type=request.form['hair_type'],

            ingredients=request.form['ingredients'],

            warning=request.form['warning'],

            buy_link=request.form['buy_link']
        )

        db.session.add(product)

        db.session.commit()

    products = Product.query.all()

    return render_template(
        'admin_products.html',
        products=products
    )
@app.route('/delete_product/<int:id>',
           methods=['POST'])

def delete_product(id):

    product = Product.query.get(id)

    db.session.delete(product)

    db.session.commit()

    return redirect('/admin/products')
@app.route("/test")
def test():
    return "Working"
if __name__ == "__main__":
    app.run(debug=True)