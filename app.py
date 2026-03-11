from flask import Flask, render_template
from config import Config
from routes.auth     import auth_bp
from routes.hr       import hr_bp
from routes.pm       import pm_bp
from routes.employee import employee_bp
from routes.admin    import admin_bp

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(auth_bp)
app.register_blueprint(hr_bp)
app.register_blueprint(pm_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(admin_bp)

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('403.html'), 404

# Pre-train ML model on startup
with app.app_context():
    try:
        from ml.train_attrition import load_model
        load_model()
        print(" Attrition ML model ready.")
    except Exception as ex:
        print(f"  ML model not loaded: {ex}")

if __name__ == '__main__':
    app.run(debug=True, port=8080)
