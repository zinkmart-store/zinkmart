from flask import Flask, render_template_string, session, redirect, send_from_directory, request
import pandas as pd
import os
from werkzeug.utils import secure_filename
import uuid
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

import os

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
conn.autocommit = True
cur = conn.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    name TEXT,
    mobile TEXT UNIQUE,
    password TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    pincode TEXT
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id SERIAL PRIMARY KEY,
    order_no TEXT UNIQUE,
    customer_name TEXT,
    mobile TEXT,
    address TEXT,
    payment TEXT,
    total NUMERIC,
    order_date TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'Pending'
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS order_items(
    id SERIAL PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER,
    product_name TEXT,
    qty INTEGER,
    price NUMERIC,
    subtotal NUMERIC
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS admin(
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS products(
    id SERIAL PRIMARY KEY,
    category TEXT,
    product TEXT,
    brand TEXT,
    unit TEXT,
    price NUMERIC,
    stock INTEGER,
    description TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS product_images(
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    image_name TEXT
)
""")

app = Flask(__name__)
app.secret_key="hitesh_store_2026"



# Excel Read
def get_products():

    cur.execute("""
    SELECT
        p.id,
        p.category,
        p.product,
        p.brand,
        p.unit,
        p.price,
        p.stock,
        p.description,
        (
            SELECT image_name
            FROM product_images pi
            WHERE pi.product_id = p.id
            ORDER BY pi.id
            LIMIT 1
        ) AS image
    FROM products p
    ORDER BY p.id
    """)
    rows = cur.fetchall()

    data = []

    for r in rows:

        data.append({
            "id": r[0],
            "category": r[1],
            "product": r[2],
            "brand": r[3],
            "unit": r[4],
            "price": float(r[5]),
            "stock": int(r[6]),
            "description": r[7],
            "image": r[8]
        })

    return data


def get_categories():

    cur.execute("""
    SELECT DISTINCT category
    FROM products
    ORDER BY category
    """)

    return [x[0] for x in cur.fetchall()]

HOME_HTML = """

<!DOCTYPE html>

<html>

<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hitesh Store</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<div class="header">

    <div class="header_top">

        <div class="menu_icon" onclick="openMenu()">
            ☰
        </div>

        <div class="logo">
            <img src="/static/logo.png" class="site_logo">
            <div class="logo_text">
                <div class="brand">zinkmart.store</div>
                <div class="tagline">Sab Milega Yha</div>
            </div>
        </div>

        <div class="cart">
            <a href="/cart">
                🛒 {{cart_count}}
            </a>
        </div>

    </div>

    <div class="search">

        <form method="GET">

            <input
                type="text"
                name="search"
                placeholder="Search Products..."
                value="{{search}}">

        </form>

    </div>

</div>


<div id="sideMenu" class="side_menu">

<span class="closebtn" onclick="closeMenu()">✖</span>

{% if session.get("user_id") %}

<h3 style="padding:20px;">
👤 {{session["user_name"]}}
</h3>

<a href="/">🏠 Home</a>

<a href="/profile">👤 My Profile</a>

<a href="/my_orders">📦 My Orders</a>

<a href="/logout">🚪 Logout</a>

{% else %}

<a href="/login">🔑 Login</a>

<a href="/register">📝 Register</a>

{% endif %}

</div>

<div class="category_bar">

<a href="/"
{% if selected_category=="All" %}
style="background:#ff9900;color:white;"
{% endif %}>
All
</a>

{% for c in categories %}

<a href="/?category={{c}}"
{% if selected_category==c %}
style="background:#ff9900;color:white;"
{% endif %}>
{{c}}
</a>

{% endfor %}

</div>


<div class="products">

{% for p in products %}

<div class="card">

<a href="/product/{{p.id}}">
    {% if p.image %}
    <img src="/product_image/{{p.image}}">
    {% else %}
    <img src="/static/no-image.png">
    {% endif %}
    </a>

<a href="/product/{{p.id}}" class="product_link">
    <h3>{{p.product}}</h3>
</a>

<p>₹ {{p.price}}</p>


<a href="/add_to_cart/{{p.id}}">
    <button>🛒 Add To Cart</button>
</a>

</div>

{% endfor %}

</div>

<script>

function openMenu(){

document.getElementById("sideMenu").style.width="260px";

}

function closeMenu(){

document.getElementById("sideMenu").style.width="0";

}

</script>

</body>

</html>

"""

@app.route("/product_image/<filename>")
def product_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")
@app.route("/")
def home():

    search = request.args.get("search", "").strip().lower()
    category = request.args.get("category", "All")

    products = get_products()

    df = pd.DataFrame(products)

    if category != "All":
        df = df[df["category"] == category]

    if search:
        df = df[df["product"].str.lower().str.contains(search)]

    data = df.to_dict("records")

    cart = session.get("cart", {})

    if not isinstance(cart, dict):
        cart = {}

    cart_count = sum(cart.values())

    return render_template_string(
        HOME_HTML,
        products=data,
        cart_count=cart_count,
        categories=get_categories(),
        selected_category=category,
        search=search,
        session=session
    )





PRODUCT_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>{{ p.product }}</title>

<link rel="stylesheet"
href="/static/style.css">

</head>

<body>

<div class="header">

    <div class="header_top">

        <a href="/" style="color:white;text-decoration:none;">
            ← Home
        </a>

        

        <div class="cart">
            <a href="/cart" style="color:white;text-decoration:none;">
                🛒 {{cart_count}}
            </a>
        </div>

    </div>

</div>


<div class="product_page">

<div class="left">

{% if images %}

<img
id="mainImage"
class="main_product_image"
src="/product_image/{{images[0][0]}}">

<div style="
display:flex;
gap:10px;
margin-top:15px;
flex-wrap:wrap;
">

{% for img in images %}

<img
class="thumb_image"
src="/product_image/{{img[0]}}"
width="45"
height="45"
style="
cursor:pointer;
border:1px solid #ddd;
border-radius:6px;
object-fit:cover;
"
onclick="
document.getElementById('mainImage').src=this.src;
">

{% endfor %}

</div>

{% else %}

<img src="/static/no-image.png">

{% endif %}

</div>

<div class="right">

<h1>{{ p['product'] }}</h1>
<p><b>Brand :</b> {{ p['brand'] }}</p>

<p><b>Unit :</b> {{ p['unit'] }}</p>

<h2>₹ {{ p['price'] }}</h2>

<p>{{ p['description'] }}</p>

<p><b>Stock :</b> {{ p['stock'] }}</p>


<br>

<div class="qty">

<button onclick="minusQty()">-</button>
<input
id="qty"
type="number"
value="1"
min="1">

<button onclick="plusQty()">+</button>
</div>

<br>

<a id="cartLink" href="/add_to_cart/{{ p.id }}?next=product">
<button class="cart_btn">
🛒 Add To Cart
</button>
</a>

<a id="buyLink" href="/buy_now/{{ p.id }}">
<button class="buy_btn">
⚡ Buy Now
</button>
</a>

</div>

</div>
<script>

function updateLinks(){

    let qty=document.getElementById("qty").value;

    document.getElementById("cartLink").href=
    "/add_to_cart/{{p.id}}?qty="+qty+"&next=product";

    document.getElementById("buyLink").href=
    "/buy_now/{{p.id}}?qty="+qty;
}

function plusQty(){

    let q=document.getElementById("qty");

    q.value=parseInt(q.value)+1;

    updateLinks();
}

function minusQty(){

    let q=document.getElementById("qty");

    if(parseInt(q.value)>1){

        q.value=parseInt(q.value)-1;

    }

    updateLinks();
}

document.getElementById("qty").addEventListener("change",updateLinks);

updateLinks();

</script>
</body>

</html>

"""

@app.route("/product/<int:id>")
def product(id):

    products = pd.DataFrame(get_products())

    df = products[products["id"] == id]

    if df.empty:
        return "Product Not Found"

    p = df.iloc[0].to_dict()

    cart = session.get("cart", {})

    if not isinstance(cart, dict):
        cart = {}

    cart_count = sum(cart.values())

    # Product ki saari images nikalo
    cur.execute("""
    SELECT image_name
    FROM product_images
    WHERE product_id=%s
    ORDER BY id
    """,(id,))

    images = cur.fetchall()

    return render_template_string(
        PRODUCT_HTML,
        p=p,
        cart_count=cart_count,
        images=images
    )

@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):

    cart = session.get("cart", {})

    # Agar purana session list hai to reset kar do
    if not isinstance(cart, dict):
        cart = {}

    key = str(id)

    qty = int(request.args.get("qty", 1))

    if key in cart:
        cart[key] += qty
    else:
        cart[key] = qty

    session["cart"] = cart

    if request.args.get("next") == "product":
        return redirect(f"/product/{id}")

    return redirect("/")

CART_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Cart</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<div class="topbar">

<a href="/">🏠 Home</a>

</div>

<h2 style="padding:20px;">🛒 Your Cart</h2>

{% if products %}

{% for p in products %}

<div class="cart_item">

{% if p.image %}
<img src="/product_image/{{p.image}}">
{% else %}
<img src="/static/no-image.png">
{% endif %}

<div>

<h3>{{p.product}}</h3>

<p>Price : ₹ {{p.price}}</p>

<div style="margin:10px 0;">

<a href="/minus/{{p.id}}">
<button style="width:40px;">-</button>
</a>

<b style="padding:0 10px;">
{{p.qty}}
</b>

<a href="/plus/{{p.id}}">
<button style="width:40px;">+</button>
</a>

</div>

<p>

Subtotal :

₹ {{p.subtotal}}

</p>

<a href="/remove/{{p.id}}">
❌ Remove
</a>

</div>

</div>

{% endfor %}

<div style="padding:20px;">

<h2>Total Items : {{products|length}}</h2>

<h2>Total ₹ {{total}}</h2>

</div>

<a href="/checkout">
<button class="buy_btn">
Proceed To Checkout
</button>
</a>

{% else %}

<h2 style="padding:20px;">
Your Cart Is Empty
</h2>

{% endif %}

</body>

</html>

"""

CHECKOUT_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Checkout</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<div class="topbar">
<a href="/cart">⬅ Back To Cart</a>
</div>

<h2 style="padding:20px;">Checkout</h2>

<form method="post">

<div style="padding:20px;max-width:500px;margin:auto;">

<input type="text" name="name" placeholder="Full Name" required><br><br>

<input type="text" name="mobile" placeholder="Mobile Number" required><br><br>

<textarea name="address" placeholder="Delivery Address" required></textarea><br><br>

<select name="payment">

<option>Cash On Delivery</option>

<option>UPI</option>

</select><br><br>

<button class="buy_btn">
Place Order
</button>

</div>

</form>

</body>

</html>

"""


@app.route("/cart")
def cart():

    cart = session.get("cart", {})

    data = []

    total = 0
    products = pd.DataFrame(get_products())
    for pid, qty in cart.items():
        
        df = products[products["id"] == int(pid)]

        if not df.empty:

            p = df.iloc[0].to_dict()

            p["qty"] = qty
            p["subtotal"] = qty * p["price"]

            total += p["subtotal"]

            data.append(p)

    return render_template_string(
        CART_HTML,
        products=data,
        total=total
    )

@app.route("/remove/<int:id>")
def remove(id):

    cart = session.get("cart", {})

    key = str(id)

    if key in cart:
        del cart[key]

    session["cart"] = cart

    return redirect("/cart")

@app.route("/buy_now/<int:id>")
def buy_now(id):

    qty = int(request.args.get("qty", 1))

    session["cart"] = {
        str(id): qty
    }

    return redirect("/cart")

@app.route("/plus/<int:id>")
def plus(id):

    cart = session.get("cart", {})

    key = str(id)

    if key in cart:
        cart[key] += 1

    session["cart"] = cart

    return redirect("/cart")


@app.route("/minus/<int:id>")
def minus(id):

    cart = session.get("cart", {})

    key = str(id)

    if key in cart:

        cart[key] -= 1

        if cart[key] <= 0:
            del cart[key]

    session["cart"] = cart

    return redirect("/cart")

LOGIN_HTML = """

<!DOCTYPE html>
<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Login</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<div class="topbar">
<a href="/">🏠 Home</a>
</div>

<h2 style="text-align:center;">Customer Login</h2>

<form method="post">

<input
type="text"
name="mobile"
placeholder="Mobile Number"
required>

<br><br>

<input
type="password"
name="password"
placeholder="Password"
required>

<br><br>

<button class="buy_btn">

Login

</button>

<br><br>

<div style="text-align:center">

<a href="/register">

Create New Account

</a>

</div>

</form>

</body>

</html>

"""

REGISTER_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Register</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<div class="topbar">
<a href="/">🏠 Home</a>
</div>

<h2 style="text-align:center;">Create Account</h2>

<form method="post">

<input
type="text"
name="name"
placeholder="Full Name"
required>

<br><br>

<input
type="text"
name="mobile"
placeholder="Mobile Number"
required>

<br><br>

<input
type="password"
name="password"
placeholder="Password"
required>

<br><br>

<input
type="text"
name="address"
placeholder="Address"
required>

<br><br>

<input
type="text"
name="city"
placeholder="City"
required>

<br><br>

<input
type="text"
name="state"
placeholder="State"
required>

<br><br>

<input
type="text"
name="pincode"
placeholder="Pincode"
required>

<br><br>

<button class="buy_btn">

Create Account

</button>

</form>

</body>

</html>

"""


@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        mobile = request.form["mobile"]
        password = request.form["password"]

        cur.execute(
            """
            SELECT id,name,password
            FROM users
            WHERE mobile=%s
            """,
            (mobile,)
        )

        user = cur.fetchone()

        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]
            session["user_name"] = user[1]

            return redirect("/")

        return "Invalid Mobile or Password"

    return render_template_string(LOGIN_HTML)
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        mobile = request.form["mobile"]
        password = generate_password_hash(request.form["password"])

        address = request.form["address"]
        city = request.form["city"]
        state = request.form["state"]
        pincode = request.form["pincode"]

        try:

            cur.execute("""
            INSERT INTO users
            (
            name,
            mobile,
            password,
            address,
            city,
            state,
            pincode
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            """,
            (
            name,
            mobile,
            password,
            address,
            city,
            state,
            pincode
            ))

            return redirect("/login")

        except:

            return "Mobile Number Already Registered"

    return render_template_string(REGISTER_HTML)

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        
        payment = request.form["payment"]
    
    
        cart = session.get("cart", {})

        total = 0
        products = pd.DataFrame(get_products())
        for pid, qty in cart.items():
            
            df = products[products["id"] == int(pid)]

            if not df.empty:

                p = df.iloc[0]

                total += int(qty) * float(p["price"])
        cur.execute("""
        SELECT name,mobile,address
        FROM users
        WHERE id=%s
        """,(session["user_id"],))

        user = cur.fetchone()

        name = user[0]
        mobile = user[1]
        address = user[2]

        payment = request.form["payment"]
        # Generate Order Number
        cur.execute("""
        SELECT COALESCE(MAX(id),0)
        FROM orders
        """)

        next_id = cur.fetchone()[0] + 1

        order_no = f"HM{next_id:06d}"
        # Save Order
        cur.execute("""
        INSERT INTO orders
        (order_no, customer_name, mobile, address, payment, total)
        VALUES(%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
            order_no,
            name,
            mobile,
            address,
            payment,
            float(total)
        ))

        order_id = cur.fetchone()[0]

        # Save Order Items
        products = pd.DataFrame(get_products())
        for pid, qty in cart.items():
            products = pd.DataFrame(get_products())
            df = products[products["id"] == int(pid)]


            if not df.empty:

                p = df.iloc[0]

                subtotal = int(qty) * float(p["price"])

                cur.execute("""
                INSERT INTO order_items
                (order_id, product_id, product_name, qty, price, subtotal)
                VALUES(%s,%s,%s,%s,%s,%s)
                """,
                (
                    int(order_id),
                    int(pid),
                    p["product"],
                    int(qty),
                    float(p["price"]),
                    float(subtotal)
                ))

        # Empty Cart
        session["cart"] = {}

        return f"""
        <html>
        <head>
        <title>Order Success</title>
        </head>

        <body style="font-family:Arial;text-align:center;padding:60px;">

        <h1>✅ Thank You {name}</h1>

        <h2>Your Order Has Been Placed Successfully.</h2>

        <h3>Order Number : {order_no}</h3>

        <br>

        <a href="/">
        <button style="
            padding:15px 30px;
            font-size:18px;
            background:#28a745;
            color:white;
            border:none;
            border-radius:8px;
            cursor:pointer;">
        Continue Shopping
        </button>
        </a>

        </body>
        </html>
        """
    return render_template_string(CHECKOUT_HTML)
@app.route("/my_orders")
def my_orders():

    if "user_id" not in session:
        return redirect("/login")

    cur.execute("""
    SELECT order_no,
           order_date,
           total,
           status
    FROM orders
    WHERE mobile = (
        SELECT mobile
        FROM users
        WHERE id=%s
    )
    ORDER BY id DESC
    """, (session["user_id"],))

    orders = cur.fetchall()

    html = """

    <html>

    <head>

    <title>My Orders</title>

    <link rel="stylesheet" href="/static/style.css">

    </head>

    <body>

    <div class="topbar">
    <a href="/">🏠 Home</a>
    </div>

    <h2 style="padding:20px;">My Orders</h2>

    """

    for o in orders:

        html += f"""

        <div class="cart_item">

        <div>

        <h3>{o[0]}</h3>
        <br>

        <a href="/my_order/{o[0]}">
        <button style="
        padding:8px 15px;
        background:#007bff;
        color:white;
        border:none;
        border-radius:5px;
        cursor:pointer;">
        View Details
        </button>
        </a>

        <br><br>

        <p>Date : {o[1]}</p>

        <p>Total : ₹ {o[2]}</p>

        <p>Status : <b>{o[3]}</b></p>

        </div>

        </div>

        """

    html += "</body></html>"

    return html
    return render_template_string(CHECKOUT_HTML)

@app.route("/my_order/<order_no>")
def my_order(order_no):

    if "user_id" not in session:
        return redirect("/login")

    cur.execute("""
    SELECT
        order_no,
        customer_name,
        mobile,
        address,
        payment,
        total,
        status,
        order_date,
        id
    FROM orders
    WHERE order_no=%s
    """,(order_no,))

    order = cur.fetchone()

    if not order:
        return "Order Not Found"

    cur.execute("""
    SELECT
        product_name,
        qty,
        price,
        subtotal
    FROM order_items
    WHERE order_id=%s
    """,(order[8],))

    items = cur.fetchall()

    html=f"""

    <html>

    <head>

    <title>My Order</title>

    <link rel="stylesheet"
    href="/static/style.css">

    </head>

    <body>

    <div class="topbar">

    <a href="/my_orders">⬅ Back</a>

    </div>

    <div style="padding:20px;">

    <h2>Order Details</h2>

    <p><b>Order No :</b> {order[0]}</p>

    <p><b>Name :</b> {order[1]}</p>

    <p><b>Mobile :</b> {order[2]}</p>

    <p><b>Address :</b> {order[3]}</p>

    <p><b>Payment :</b> {order[4]}</p>

    <p><b>Status :</b> {order[6]}</p>

    <p><b>Date :</b> {order[7]}</p>

    <hr>

    <h3>Products</h3>

    """

    for i in items:

        html += f"""

        <div class="cart_item">

        <div>

        <h3>{i[0]}</h3>

        <p>Qty : {i[1]}</p>

        <p>Price : ₹ {i[2]}</p>

        <p>Subtotal : ₹ {i[3]}</p>

        </div>

        </div>

        """

    html += f"""

    <hr>

    <h2>Total : ₹ {order[5]}</h2>

    </div>

    </body>

    </html>

    """

    return html

@app.route("/admin", methods=["GET","POST"])
def admin():

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        cur.execute("""
        SELECT id
        FROM admin
        WHERE username=%s
        AND password=%s
        """,(username,password))

        row=cur.fetchone()

        if row:

            session["admin"]=True

            return redirect("/admin/orders")
        return "Invalid Login"

    return render_template_string(ADMIN_LOGIN_HTML)


ADMIN_LOGIN_HTML = """

<html>

<head>

<title>Admin Login</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<h2 style="text-align:center;">Admin Login</h2>

<form method="post" class="form_box">

<input
type="text"
name="username"
placeholder="Username"
required>

<br><br>

<input
type="password"
name="password"
placeholder="Password"
required>

<br><br>

<button class="buy_btn">

Login

</button>

</form>

</body>

</html>

"""
@app.route("/admin/orders")
def admin_orders():

    if "admin" not in session:
        return redirect("/admin")

    cur.execute("""
    SELECT
        id,
        order_no,
        customer_name,
        mobile,
        total,
        payment,
        status,
        order_date
    FROM orders
    ORDER BY id DESC
    """)

    orders = cur.fetchall()

    html = """

    <html>

    <head>

    <title>All Orders</title>

    <link rel="stylesheet" href="/static/style.css">

    </head>

    <body>

    <div class="topbar">

    <a href="/admin/inventory">📦 Inventory</a>

    &nbsp;&nbsp;

    <a href="/admin/products">🛒 Products</a>

    &nbsp;&nbsp;

    
    </div>

    <h2 style="padding:20px;">Order Register</h2>

    <table border="1" width="100%" cellspacing="0" cellpadding="8">

    <tr style="background:#f2f2f2;">

    <th>Sr</th>
    <th>Order No</th>
    <th>Date</th>
    <th>Customer</th>
    <th>Mobile</th>
    <th>Total</th>
    <th>Payment</th>
    <th>Status</th>
    <th>Action</th>

    </tr>

    """

    sr = 1

    for o in orders:

        html += f"""

        <tr>

        <td>{sr}</td>

        <td>{o[1]}</td>

        <td>{o[7].strftime('%d-%m-%Y')}</td>

        <td>{o[2]}</td>

        <td>{o[3]}</td>

        <td>₹ {o[4]}</td>

        <td>{o[5]}</td>

        <td>{o[6]}</td>

        <td>

        <a href="/admin/order/{o[0]}">👁 View</a>

        <br><br>

        <a href="/status/{o[0]}/Packed">Packed</a> |

        <a href="/status/{o[0]}/Shipped">Shipped</a> |

        <a href="/status/{o[0]}/Delivered">Delivered</a>

        </td>

        </tr>

        """

        sr += 1

    html += """

    </table>

    </body>

    </html>

    """

    return html
@app.route("/admin/order/<int:id>")
def admin_order(id):

    if "admin" not in session:
        return redirect("/admin")

    # Order Details
    cur.execute("""
    SELECT
        order_no,
        customer_name,
        mobile,
        address,
        payment,
        total,
        status,
        order_date
    FROM orders
    WHERE id=%s
    """,(id,))

    order = cur.fetchone()

    # Products
    cur.execute("""
    SELECT
        product_name,
        qty,
        price,
        subtotal
    FROM order_items
    WHERE order_id=%s
    """,(id,))

    items = cur.fetchall()

    html=f"""

    <html>

    <head>

    <title>Invoice</title>

    <link rel="stylesheet"
    href="/static/style.css">

    </head>

    <body>

    <div class="topbar">

    <a href="/admin/orders">

    ← Back

    </a>

    </div>

    <h2 style="padding:20px;">

    Order Invoice

    </h2>

    <div class="cart_item">

    <h3>Order No : {order[0]}</h3>

    <p><b>Name :</b> {order[1]}</p>

    <p><b>Mobile :</b> {order[2]}</p>

    <p><b>Address :</b> {order[3]}</p>

    <p><b>Payment :</b> {order[4]}</p>

    <p><b>Status :</b> {order[6]}</p>

    <p><b>Date :</b> {order[7]}</p>

    <hr>

    <h3>Products</h3>

    """

    for i in items:

        html+=f"""

        <div style="padding:10px;border-bottom:1px solid #ddd;">

        <b>{i[0]}</b>

        <br>

        Qty : {i[1]}

        <br>

        Price : ₹ {i[2]}

        <br>

        Subtotal : ₹ {i[3]}

        </div>

        """

    html+=f"""

    <hr>

    <h2>Total : ₹ {order[5]}</h2>

    <br>

    <button onclick="window.print()"
    class="buy_btn">

    Print Invoice

    </button>

    </div>

    </body>

    </html>

    """

    return html

PRODUCT_REGISTER_HTML = """

<html>

<head>

<title>Product Register</title>

<link rel="stylesheet" href="/static/style.css">

</head>

<body>

<div class="topbar">

<a href="/admin/orders">📦 Orders</a>

&nbsp;&nbsp;&nbsp;



<a href="/admin/inventory">📦 Inventory</a>

</div>

<h2 style="padding:20px;">Product Register</h2>

<form method="post" enctype="multipart/form-data">

<input type="text" name="category" placeholder="Category" required><br><br>

<input type="text" name="product" placeholder="Product Name" required><br><br>

<input type="text" name="brand" placeholder="Brand" required><br><br>

<input type="text" name="unit" placeholder="Unit" required><br><br>

<input type="number" step="0.01" name="price" placeholder="Price" required><br><br>

<input type="number" name="stock" placeholder="Stock" required><br><br>
<br><br>

<input
type="number"
name="opening_stock"
placeholder="Opening Stock"
value="0">

<br><br>

<input
type="number"
name="minimum_stock"
placeholder="Minimum Stock Alert"
value="5">

<br><br>

<textarea
name="description"
placeholder="Description"></textarea>

<br><br>

<input
type="file"
name="images"
multiple>

<br><br>

<button class="buy_btn">

Save Product

</button>

</form>
<hr>

<h2>Product List</h2>

<table border="1" width="100%" cellpadding="8">

<tr style="background:#f2f2f2">

<th>Sr</th>
<th>Category</th>
<th>Product</th>
<th>Brand</th>
<th>Unit</th>
<th>Price</th>
<th>Stock</th>
<th>Photo</th>
<th>Action</th>


</tr>

{% for p in products %}

<tr>

<td>{{p[0]}}</td>

<td>{{p[1]}}</td>

<td>{{p[2]}}</td>

<td>{{p[3]}}</td>

<td>{{p[4]}}</td>

<td>₹ {{p[5]}}</td>

<td>{{p[6]}}</td>
<td>

{% if p[7] %}

<img
src="/product_image/{{p[7]}}"
width="70"
height="70"
style="
object-fit:cover;
border-radius:8px;
border:1px solid #ddd;
">

{% else %}

No Image

{% endif %}

</td>

<td>

<a href="/admin/edit_product/{{p[0]}}">✏ Edit</a>

|

<a href="/admin/delete_product/{{p[0]}}"
onclick="return confirm('Delete Product?')">

❌ Delete

</a>

</td>

</tr>

{% endfor %}

</table>
</body>

</html>

"""
@app.route("/admin/products", methods=["GET","POST"])
def admin_products():

    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":

        category = request.form["category"]
        product = request.form["product"]
        brand = request.form["brand"]
        unit = request.form["unit"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        opening_stock = int(request.form["opening_stock"])

        minimum_stock = int(request.form["minimum_stock"])
        description = request.form["description"]

        cur.execute("""
        INSERT INTO products
        (
        category,
        product,
        brand,
        unit,
        price,
        stock,
        opening_stock,
        minimum_stock,
        description
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
        category,
        product,
        brand,
        unit,
        price,
        stock,
        opening_stock,
        minimum_stock,
        description
        ))

        product_id = cur.fetchone()[0]

        files = request.files.getlist("images")

        for file in files:

            if file.filename:

                filename = secure_filename(file.filename)

                ext = filename.rsplit(".",1)[1]

                new_name = f"{uuid.uuid4()}.{ext}"

                file.save(os.path.join(UPLOAD_FOLDER,new_name))

                cur.execute("""
                INSERT INTO product_images
                (
                product_id,
                image_name
                )
                VALUES(%s,%s)
                """,
                (
                product_id,
                new_name
                ))
        return redirect("/admin/products")

    cur.execute("""
    SELECT
        p.id,
        p.category,
        p.product,
        p.brand,
        p.unit,
        p.price,
        p.stock,
        (
            SELECT image_name
            FROM product_images pi
            WHERE pi.product_id = p.id
            LIMIT 1
        ) AS image
    FROM products p
    ORDER BY p.id DESC
    """)

    products = cur.fetchall()

    return render_template_string(
        PRODUCT_REGISTER_HTML,
        products=products
    )

@app.route("/admin/delete_product/<int:id>")
def delete_product(id):

    if "admin" not in session:
        return redirect("/admin")

    cur.execute("""
    DELETE FROM product_images
    WHERE product_id=%s
    """,(id,))

    cur.execute("""
    DELETE FROM products
    WHERE id=%s
    """,(id,))

    return redirect("/admin/products")

@app.route("/admin/edit_product/<int:id>", methods=["GET","POST"])
def edit_product(id):

    if "admin" not in session:
        return redirect("/admin")

    if request.method=="POST":

        cur.execute("""
        UPDATE products
        SET
            category=%s,
            product=%s,
            brand=%s,
            unit=%s,
            price=%s,
            stock=%s,
            description=%s
        WHERE id=%s
        """,
        (
            request.form["category"],
            request.form["product"],
            request.form["brand"],
            request.form["unit"],
            float(request.form["price"]),
            int(request.form["stock"]),
            request.form["description"],
            id
        ))
        files = request.files.getlist("images")

        for file in files:

            if file.filename:

                filename = secure_filename(file.filename)

                ext = filename.rsplit(".",1)[1]

                new_name = f"{uuid.uuid4()}.{ext}"

                file.save(os.path.join(UPLOAD_FOLDER,new_name))

                cur.execute("""
                INSERT INTO product_images
                (
                    product_id,
                    image_name
                )
                VALUES(%s,%s)
                """,
                (
                    id,
                    new_name
                ))
        return redirect("/admin/products")

    cur.execute("""
    SELECT
        category,
        product,
        brand,
        unit,
        price,
        stock,
        description
    FROM products
    WHERE id=%s
    """,(id,))

    p = cur.fetchone()
    cur.execute("""
    SELECT
        id,
        image_name
    FROM product_images
    WHERE product_id=%s
    ORDER BY id
    """, (id,))

    images = cur.fetchall()

    return f"""
    <html>

    <head>

    <link rel="stylesheet"
    href="/static/style.css">

    </head>

    <body>

    <h2 style="padding:20px;">
    Edit Product
    </h2>

    <form method="post" enctype="multipart/form-data">

    <input name="category" value="{p[0]}"><br><br>

    <input name="product" value="{p[1]}"><br><br>

    <input name="brand" value="{p[2]}"><br><br>

    <input name="unit" value="{p[3]}"><br><br>

    <input
    name="price"
    value="{p[4]}"><br><br>

    <input
    name="stock"
    value="{p[5]}"><br><br>

    <textarea
    name="description">{p[6]}</textarea>

    <br><br>
    <h3>Current Images</h3>

    <div style="display:flex;gap:15px;flex-wrap:wrap;">

    {
    ''.join(f'''

    <div style="text-align:center;">

    <img
    src="/product_image/{img[1]}"
    width="120"
    height="120"
    style="object-fit:cover;border-radius:8px;border:1px solid #ddd;">

    <br><br>

    <a href="/admin/delete_image/{img[0]}"
    style="
    background:red;
    color:white;
    padding:6px 12px;
    text-decoration:none;
    border-radius:5px;
    ">
    Delete
    </a>

    </div>

    ''' for img in images)
    }

    </div>

    <br><br>
    <h3>Upload New Images</h3>

    <input
    type="file"
    name="images"
    multiple>

    <br><br>

    <br><br>

    <button class="buy_btn">

    Update Product

    </button>

    </form>

    </body>

    </html>
    """
@app.route("/admin/delete_image/<int:image_id>")
def delete_image(image_id):

    if "admin" not in session:
        return redirect("/admin")

    cur.execute("""
    SELECT
        product_id,
        image_name
    FROM product_images
    WHERE id=%s
    """, (image_id,))

    row = cur.fetchone()

    if row:

        image_path = os.path.join(UPLOAD_FOLDER, row[1])

        if os.path.exists(image_path):
            os.remove(image_path)

        cur.execute("""
        DELETE FROM product_images
        WHERE id=%s
        """, (image_id,))

        return redirect(f"/admin/edit_product/{row[0]}")

    return redirect("/admin/products")
@app.route("/status/<int:id>/<status>")
def status(id,status):

    if "admin" not in session:

        return redirect("/admin")

    cur.execute("""
    UPDATE orders
    SET status=%s
    WHERE id=%s
    """,(status,id))
    if status == "Delivered":

        cur.execute("""
        SELECT product_id, qty
        FROM order_items
        WHERE order_id=%s
        """,(id,))

        items = cur.fetchall()

        for item in items:

            cur.execute("""
            UPDATE products
            SET
                stock = stock - %s,
                sold_qty = sold_qty + %s
            WHERE id=%s
            """,
            (
                item[1],
                item[1],
                item[0]
            ))

    return redirect("/admin/orders")
@app.route("/admin/inventory")
def inventory():

    if "admin" not in session:
        return redirect("/admin")

    cur.execute("""
    SELECT
        p.id,
        (
            SELECT image_name
            FROM product_images pi
            WHERE pi.product_id=p.id
            LIMIT 1
        ),
        p.product,
        p.opening_stock,
        p.purchase_qty,
        p.sold_qty,
        p.stock,
        p.minimum_stock
    FROM products p
    ORDER BY p.product
    """)

    items = cur.fetchall()

    html = """

    <html>

    <head>

    <title>Inventory</title>

    <link rel="stylesheet" href="/static/style.css">

    </head>

    <body>

    <div class="topbar">

    <a href="/admin/products">🛒 Products</a>

    &nbsp;&nbsp;

    <a href="/admin/orders">📦 Orders</a>
    <a href="/admin/customers">👥 Customers</a>

    </div>

    <h2 style="padding:20px;">
    Inventory Register
    </h2>

    <table border="1"
    cellspacing="0"
    cellpadding="10"
    width="100%">

    <tr>

    <th>Sr</th>

    <th>Photo</th>

    <th>Product</th>

    <th>Opening</th>

    <th>Purchase</th>

    <th>Sale</th>

    <th>Closing</th>

    <th>Status</th>

    </tr>

    """

    sr = 1

    for i in items:

        if i[7] >= i[6]:

            status = "🔴 Low"

        else:

            status = "🟢 OK"

        image = ""

        if i[1]:

            image = f'<img src="/product_image/{i[1]}" width="60">'

        html += f"""

        <tr>

        <td>{sr}</td>

        <td>{image}</td>

        <td>{i[2]}</td>

        <td>{i[3]}</td>

        <td>{i[4]}</td>

        <td>{i[5]}</td>

        <td>{i[6]}</td>

        <td>{status}</td>

        </tr>

        """

        sr += 1

    html += """

    </table>

    </body>

    </html>

    """

    return html

@app.route("/admin/customers")
def admin_customers():

    if "admin" not in session:
        return redirect("/admin")

    cur.execute("""
    SELECT
        u.id,
        u.name,
        u.mobile,
        u.city,
        COUNT(o.id) AS total_orders,
        COALESCE(SUM(o.total),0) AS total_amount
    FROM users u
    LEFT JOIN orders o
        ON u.mobile = o.mobile
    GROUP BY
        u.id,
        u.name,
        u.mobile,
        u.city
    ORDER BY u.name
    """)

    customers = cur.fetchall()

    html = """
    <html>
    <head>
        <title>Customers</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>

    <div class="topbar">
        <a href="/admin/products">🛒 Products</a>
        &nbsp;&nbsp;
        <a href="/admin/orders">📦 Orders</a>
        &nbsp;&nbsp;
        <a href="/admin/customers">👥 Customers</a>
    </div>

    <h2 style="padding:20px;">Customer Register</h2>

    <table border="1" width="100%" cellspacing="0" cellpadding="10">

    <tr>
        <th>Sr</th>
        <th>Name</th>
        <th>Mobile</th>
        <th>City</th>
        <th>Total Orders</th>
        <th>Total Amount</th>
    </tr>
    """

    sr = 1

    for c in customers:

        html += f"""
        <tr>
            <td>{sr}</td>
            <td>{c[1]}</td>
            <td>{c[2]}</td>
            <td>{c[3] or ''}</td>
            <td>{c[4]}</td>
            <td>₹ {c[5]}</td>
        </tr>
        """

        sr += 1

    html += """
    </table>

    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app.run()