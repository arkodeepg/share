from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

import requests

import os,csv
from helpers import login_required


app = Flask(__name__)
app.debug=True


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database

# database engine object from SQLAlchemy that manages connections to the database
engine = create_engine(os.getenv("DATABASE_URL"))

# create a 'scoped session' that ensures different users' interactions with the
# database are kept separate
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")

def index():
    return render_template("index.html",message="if you had not register yet please register yourself and login after that")
@app.route("/login",methods=["GET","POST"])
def login():

    if request.method=="POST":
        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")
        elif not request.form.get("password"):
            return render_template("error.html",message="must provide password")
        rows=db.execute("SELECT * FROM users WHERE username=:username",{"username":request.form.get("username")})
        result=rows.fetchone()

        if result ==None or not check_password_hash(result[2],request.form.get("password")):
            return render_template("error.html",message="password do not match")
        session["user_id"]=result[0]
        session["username"]=result[1]
        return render_template("index.html",message="you have successfully LOG_IN")
    else:
        return render_template("login.html")
@app.route("/logout",methods=["GET"])
def logout():

    """ Log user out """

     #Forget any user ID
    session.clear()


     #Redirect user to login form
    return redirect("/")


@app.route("/register",methods=["GET","POST"])

def register():
    """ Register user """





    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")
        usercheck=db.execute("SELECT * FROM users WHERE username=:username",{"username":request.form.get("username")}).fetchone()
        if usercheck :
            return render_template("error.html",message="username taken")
        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")
        hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                            {"username":request.form.get("username"),
                             "password":hashedPassword})
        db.commit()
        return render_template("index.html",message="you have successfully registered.now login ")
    else:
        return render_template("register.html")
@app.route("/search",methods=["GET","POST"])
@login_required
def search():
    if not request.args.get("book"):
        return render_template("error.html", message="you must provide a book.")
    query = "%" + request.args.get("book") + "%"
    query=query.title()
    rows=db.execute(" SELECT isbn, title, author, year FROM books WHERE  isbn LIKE :query or  title LIKE :query or  author LIKE :query ",{"query":query}).fetchall()
    if len(rows) == 0:
        return render_template("error.html", message="we can't find books with that description.")
    else:
        return render_template("results.html",books =rows)
@app.route("/book/<isbn>",methods=["GET","POST"])
def book(isbn):
    if request.method=="POST":
        currentUser=session["user_id"]
        rating=request.form.get("rating")
        comment=request.form.get("comment")
        row1=db.execute("SELECT id FROM books WHERE isbn=:isbn",{"isbn":isbn})
        bookId=row1.fetchone()
        bookId=bookId[0]
        row2=db.execute("SELECT * FROM reviews WHERE user_id=:user_id",{"user_id":currentUser})
        if row2.rowcount==1:
            print("suck bitch")
            return render_template("error.html",message="you have submited more than one review")
        rating=int(rating)
        db.execute("INSERT INTO reviews (user_id,book_id,comment,rating) VALUES (:user_id,:book_id,:comment,:rating)",{"user_id":currentUser,"book_id":bookId,"comment":comment,"rating":rating})
        db.commit()
        flash("review submitted")
        return render_template("index.html",message="successfully submited review")
    else:
        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})

        bookInfo = row.fetchall()

        """ GOODREADS reviews """

        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")

        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

        # Convert the response to JSON
        response = query.json()

        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

        # Append it as the second element on the list. [1]
        bookInfo.append(response)

        """ Users reviews """

         # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save id into variable
        book = row.fetchone() # (id,)
        book = book[0]

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)


        results = db.execute("SELECT users.username, comment, rating FROM users INNER JOIN reviews ON users.id = reviews.user_id WHERE book_id = :book ",{"book": book})

        reviews = results.fetchall()

        return render_template("books.html", bookInfo=bookInfo, reviews=reviews)



if __name__=='__main__':

    app.run(debug=True)
