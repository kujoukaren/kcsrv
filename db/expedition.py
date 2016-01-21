from . import db
from sqlalchemy.dialects.postgresql import JSONB

admiral_expedition_asoc = db.Table('admiral_j_expedition',
    db.Column('adm_id', db.Integer, db.ForeignKey('admiral.id')),
    db.Column('expedition_id', db.Integer, db.ForeignKey('expedition.id'))
)


class Expedition(db.Model):
    """An expedition."""
    id = db.Column(db.Integer, primary_key=True)

    resources_id = db.Column(db.ForeignKey('resources.id'))
    resources_granted = db.relationship('Resources')

    # Constraints on what ships there can be, resources, etc
    constraints = db.Column(JSONB)
