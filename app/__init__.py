from flask import Flask, request, url_for
from app.extensions import db, migrate
from app.routes import bp
from werkzeug.routing import BuildError


def create_app():
    app = Flask(__name__)

#    def switch_country_url(new_country):
#        try:
#            if not request.endpoint:
#                return url_for('main.country_home', country=new_country)
#
#            view_args = dict(request.view_args or {})
#            view_args['country'] = new_country
#
#            # preserve query string like ?sort=price
#            if request.args:
#                view_args.update(request.args.to_dict())
#
#            return url_for(request.endpoint, **view_args)
#
#        except BuildError:
#            return url_for('main.country_home', country=new_country)
#        
#
#    app.jinja_env.globals['switch_country_url'] = switch_country_url
#    
    
    app.config.from_object("app.config.Config")
    db.init_app(app)
    migrate.init_app(app, db)   

    app.register_blueprint(bp)

    return app