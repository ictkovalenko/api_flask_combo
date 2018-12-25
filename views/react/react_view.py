from flask import render_template, redirect
from flaskapp import app
from views.util import login_required


@app.route('/')
def view_root():
    return redirect('/r/')


@app.route('/r/')
def view_react_root():
    return render_template('react/root.html')


@app.route('/r/<path:path>')
def view_react_root2(path):
    return render_template('react/root.html')


@app.route('/dev')
def view_react_root3():
    return render_template('react/root.html')


@app.route('/dev/<path:path>')
def view_react_root4(path):
    return render_template('react/root.html')


@app.route('/view_app')
def view_view_app():
    return render_template('react/view_app.html')
