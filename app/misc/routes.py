from flask import Blueprint, render_template

misc_bp = Blueprint('misc', __name__, template_folder='../../templates')


@misc_bp.route('/notificaciones')
def notifications():
    return render_template('notifications.html')


@misc_bp.route('/solicitudes')
@misc_bp.route('/admin/solicitudes')
def solicitudes():
    return render_template('admin_solicitudes.html')
