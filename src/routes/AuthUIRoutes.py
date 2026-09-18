from flask import Blueprint, redirect, render_template


def create_auth_ui_blueprint() -> Blueprint:
    blueprint = Blueprint("auth_ui", __name__)

    @blueprint.get("/login")
    def login_page():
        return render_template("auth/login.html")

    @blueprint.get("/register")
    def register_page():
        return render_template("auth/register.html")

    @blueprint.get("/account")
    def account_redirect():
        return redirect("/chat")

    return blueprint
