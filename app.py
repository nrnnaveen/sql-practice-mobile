from flask import Flask,render_template,request,redirect,session

from auth import create_user,check_login
from mysql_engine import run_query as mysql_query
from postgres_engine import run_query as pg_query

app=Flask(__name__)
app.secret_key="sqlpractice"

@app.route("/")
def home():
    return render_template("login.html")


@app.route("/signup",methods=["GET","POST"])
def signup():

    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]

        create_user(email,password)

        return redirect("/")

    return render_template("signup.html")


@app.route("/login",methods=["POST"])
def login():

    email=request.form["email"]
    password=request.form["password"]

    if check_login(email,password):

        session["user"]=email
        return redirect("/dashboard")

    return "Login failed"


@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    return render_template("dashboard.html")


@app.route("/editor",methods=["GET","POST"])
def editor():

    columns=[]
    rows=[]

    if request.method=="POST":

        db=request.form["database"]
        query=request.form["query"]

        if db=="mysql":
            columns,rows=mysql_query(query)

        if db=="postgres":
            columns,rows=pg_query(query)

    return render_template("editor.html",columns=columns,rows=rows)


app.run(host="0.0.0.0",port=5000)
