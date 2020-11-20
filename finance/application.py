import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Not secure
API_KEY="pk_586454e8fc50424abaa73cd162c7cd7d"

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    # Query for each stock and how many of it the user has
    stocks = db.execute("SELECT stock, shares FROM portfolio WHERE user_id = :user_id",
        user_id = user_id);

    # Query for the amount of cash the user has
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id",
        user_id = user_id)[0]["cash"];

    # Starting user's holdings with the cash amount
    holdings = cash

    # Populating a list with a dictionary for each stock the user has
    list_of_stocks = []

    for stock in stocks:
        symbol = stock["stock"]
        quote = lookup(symbol)

        list_of_stocks.append({
        'symbol': quote["symbol"],
        'quote': lookup(symbol),
        'name': quote["name"],
        'shares': stock["shares"],
        'price': usd(quote["price"]),
        'total': usd(stock["shares"] * quote["price"])
        })

        # Adding the stocks values to user's holdings
        holdings += stock["shares"] * quote["price"]

    # Formatting to USD
    holdings = usd(holdings)
    cash = usd(cash)

    return render_template("index.html",
        stocks = list_of_stocks, holdings = holdings, cash = cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Check Stock
        quote = lookup(request.form.get("symbol"))
        if quote == None or quote == "":
            return apology("Invalid stock symbol", 403)

        # Check number of shares
        number_of_shares = int(request.form.get("shares"))

        # Check if user has enough money
        user_id = session["user_id"]
        price = quote["price"]
        final_price = int(price) * number_of_shares
        avaiable_cash = db.execute("SELECT cash FROM users WHERE id = :user_id",
                                    user_id = user_id)[0]["cash"];
        if final_price > avaiable_cash:
            return apology("Not enough money", 403)

        else:
            # Add to user's portfolio

            # If user has shares of company
            if db.execute("SELECT * FROM portfolio WHERE user_id = :user_id AND stock = :symbol",
                    user_id = user_id, symbol = quote["symbol"]):
                db.execute("UPDATE portfolio SET shares = shares + :shares WHERE stock = :symbol AND user_id = :user_id",
                    user_id = user_id, symbol = quote["symbol"], shares = number_of_shares);
            else:
                db.execute("INSERT INTO portfolio (stock, shares, user_id) VALUES (:stock, :shares, :user_id)",
                    stock = quote["symbol"], shares = number_of_shares, user_id = user_id);

            # Update user's cash
            total_price = quote["price"] * number_of_shares
            db.execute("UPDATE users SET cash = cash - :total_price WHERE id = :user_id",
                    total_price = total_price, user_id = user_id);

            # Add to user history
            date = datetime.now()
            db.execute("INSERT INTO history (stock, shares, price, transacted, user_id) VALUES (:stock, :shares, :price, :transacted, :user_id)",
                    stock = quote["symbol"], shares = number_of_shares, price = total_price, transacted = date, user_id = user_id);

            return redirect("/")

    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    # Query for each transaction the user has made
    transactions = db.execute("SELECT * FROM history WHERE user_id = :user_id ORDER BY id DESC",
        user_id = user_id);

    # Populating a list with a dictionary for each transaction
    list_of_transactions = []

    for trade in transactions:
        list_of_transactions.append({
        'stock': trade["stock"],
        'shares': trade["shares"],
        'price': usd(trade["price"]),
        'transacted': trade["transacted"]
        })

    return render_template("history.html", transactions = list_of_transactions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST
    if request.method == "POST":

        # Ensure stock symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 403)

        #Pull stock from API and make sure it's valid
        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("Invalid stock symbol", 403)
        else:
            price = usd(quote["price"])
            return render_template("quoted.html", quote=quote, price=price)

    # User reached route via GET
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached reached route via POST
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password meet requirements
        elif len(request.form.get("password")) < 6:
            return apology("Password needs to be bigger or equal to six characters", 403)

        # Ensure password and confirmation match
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("Passwords don't match", 403)

        #Ensure username is unique
        elif db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username")):
            return apology("Username taken", 403)

        #Insert user in database with hashed password
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                username=request.form.get("username"),
                hash=generate_password_hash(request.form.get("password")));
            return redirect("/")

    # User reached reached route via GET
    if request.method == "GET":
        return render_template("/register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":

        # Check if user has enough shares to sell
        req_shares = request.form.get("shares")
        stock = request.form.get("symbol")

        if stock == None or req_shares == None:
            return apology("Blank form", 403)

        own_shares = db.execute("SELECT shares FROM portfolio WHERE user_id = :user_id AND stock = :stock",
            user_id = user_id, stock = stock);

        if req_shares > str(own_shares):
            return apology("Not enough shares", 403)

        # Actually sell
        else:
            quote = lookup(stock)
            date = datetime.now()

            # Update user's cash
            total_price = quote["price"] * int(req_shares)
            db.execute("UPDATE users SET cash = cash + :total_price WHERE id = :user_id",
                    total_price = total_price, user_id = user_id);

            # Update user's portfolio
            db.execute("UPDATE portfolio SET shares = shares - :req_shares WHERE user_id = :user_id AND stock = :symbol",
                    req_shares = req_shares, user_id = user_id, symbol = stock);

            # Save transaction into history
            db.execute("INSERT INTO history (stock, shares, price, transacted, user_id) VALUES (:stock, :shares, :price, :transacted, :user_id)",
                    stock = stock, shares = "-" + req_shares, price = total_price, transacted = date, user_id = user_id);

            return redirect("/")

    # Render page
    else:

        stocks = db.execute("SELECT stock FROM portfolio WHERE user_id = :user_id",
        user_id = user_id);

        return render_template("sell.html", stocks = stocks)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Manage Account Settings"""

    return render_template("settings.html")

@app.route("/add-cash", methods=["POST"])
@login_required
def addCash():
    """Manage Account Settings"""
    user_id = session["user_id"]

    # Updates user's cash and returns to index
    amount = request.form.get("add-cash")
    db.execute("UPDATE users SET cash = cash + :amount WHERE id = :user_id",
                    amount = amount, user_id = user_id);

    # Add to user history
    date = datetime.now()
    db.execute("INSERT INTO history (stock, shares, price, transacted, user_id) VALUES (:stock, :shares, :price, :transacted, :user_id)",
            stock = "ADD", shares = "CASH", price = amount, transacted = date, user_id = user_id);

    return redirect("/")

@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    """Manage Account Settings"""
    user_id = session["user_id"]

    # Updates user's cash and returns to index
    amount = request.form.get("withdraw")
    db.execute("UPDATE users SET cash = cash - :amount WHERE id = :user_id",
                    amount = amount, user_id = user_id);

    # Add to user history
    date = datetime.now()
    db.execute("INSERT INTO history (stock, shares, price, transacted, user_id) VALUES (:stock, :shares, :price, :transacted, :user_id)",
            stock = "DRAW", shares = "CASH", price = "-" + amount, transacted = date, user_id = user_id);

    return redirect("/")

@app.route("/change-password", methods=["POST"])
@login_required
def newPassword():
    """Manage Account Settings"""
    user_id = session["user_id"]

    # Query database for username
    rows = db.execute("SELECT * FROM users WHERE username = :username",
                username=request.form.get("username"))

    # Ensure username exists and password is correct
    if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("old-password")):
        return apology("invalid username and/or password", 403)

    if not request.form.get("password"):
            return apology("must provide password", 403)

    # Ensure password meet requirements
    if len(request.form.get("password")) < 6:
        return apology("Password needs to be bigger or equal to six characters", 403)

    # Ensure password and confirmation match
    elif request.form.get("confirmation") != request.form.get("password"):
        return apology("Passwords don't match", 403)

    db.execute("UPDATE users SET hash = :hash WHERE id = :user_id",
            hash=generate_password_hash(request.form.get("password")), user_id = user_id);

    return redirect("/")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
