from flask import request, g, Blueprint, abort

import helpers.MemberHelper
from db import Admiral
from db import db, Kanmusu
from helpers import _QuestHelper, AdmiralHelper, DockHelper, MemberHelper
from util import prepare_api_blueprint
from util import svdata

api_actions = Blueprint('api_actions', __name__)


@api_actions.route('/api_port/port', methods=['GET', 'POST'])
def port():
    return svdata(helpers.MemberHelper.port())


@api_actions.route('/api_req_kaisou/slotset', methods=['GET', 'POST'])
# Change Item
def slotset():
    id = request.values.get("api_id")
    equip_id = request.values.get("api_item_id")
    slot = request.values.get("api_slot_idx")

    Kanmusu.get(id).equip(admiral_equip_id=equip_id, slot=slot)
    db.session.commit()
    return svdata({})


@api_actions.route('/api_req_kaisou/powerup', methods=['GET', 'POST'])
# Modernization
def powerup():
    id = request.values.get("api_id")
    id_items = request.values.get("api_id_items").split(',')  # How mean girls aren't items
    result = Kanmusu.get(id).modernize(id_items)
    db.session.commit()
    return svdata(MemberHelper.powerup(id, result))


@api_actions.route('/api_req_kaisou/remodeling', methods=['GET', 'POST'])
# Remodeling
def remodeling():
    id = request.values.get("api_id")
    Kanmusu.get(id).remodel()  # If it only were that easy...
    return svdata({})


@api_actions.route('/api_req_hensei/lock', methods=['POST'])
def lock():
    """Heartlock/unheartlock a ship."""
    kanmusu = g.admiral.kanmusu.filter_by(number=int(request.values.get("api_ship_id")) - 1).first_or_404()

    kanmusu.locked = not kanmusu.locked

    db.session.add(kanmusu)
    db.session.commit()
    return svdata({"api_locked": int(kanmusu.locked)})


@api_actions.route('/api_req_kousyou/createship', methods=['POST'])
def build():
    fuel = int(request.values.get("api_item1"))
    ammo = int(request.values.get("api_item2"))
    steel = int(request.values.get("api_item3"))
    baux = int(request.values.get("api_item4"))
    dock = int(request.values.get("api_kdock_id"))  # -1 # For some reason, it doesn't need minusing one. ¯\_(ツ)_/¯
    DockHelper.craft_ship(fuel, ammo, steel, baux, dock)
    return svdata({})


@api_actions.route('/api_req_kousyou/getship', methods=['POST'])
def getship():
    dock = int(request.values.get("api_kdock_id"))
    try:
        data = DockHelper.get_and_remove_ship(dockid=dock)
    except (IndexError, AttributeError):
        return svdata({}, code=201, message='申し訳ありませんがブラウザを再起動し再ログインしてください。')
    return svdata(data)


@api_actions.route('/api_req_hensei/change', methods=['GET', 'POST'])
def change_pos():
    # This is a lot cleaner than before.
    # Known bug: You cannot switch sometimes properly, when changing ship with one in your library.

    # Get data from request.
    fleet_id = int(request.values.get("api_id")) - 1
    ship_id = int(request.values.get("api_ship_id")) - 1
    ship_pos = int(request.values.get("api_ship_idx"))

    if ship_pos > 5:
        abort(400)
    if fleet_id > 4:
        abort(400)

    # Get the fleet.
    try:
        fleet = g.admiral.fleets[fleet_id]
    except IndexError:
        abort(404)
        return

    # Find the ship with id `ship_id`.
    try:
        if ship_id != -2:
            kmsu = g.admiral.kanmusu[ship_id]
        else:
            kmsu = None
    except:
        abort(404)
        return

    # Finally, get the ship at `ship_pos` of fleet.
    try:
        kmsu2 = fleet.kanmusu[ship_pos]
    except IndexError:
        kmsu2 = None

    # Check if it's already in the fleet.
    if kmsu and not kmsu in fleet.kanmusu:
        kmsu.fleet_position = len(fleet.kanmusu)
        fleet.kanmusu.append(kmsu)
        db.session.add(kmsu)
        db.session.commit()
        return svdata({})

    if kmsu:
        current_ship_pos = kmsu.fleet_position
    elif kmsu2:
        current_ship_pos = kmsu2.fleet_position
    else:
        current_ship_pos = None

    # Check if it's a removal.
    if ship_id == -2:
        # We cannot use the loaded `kmsu`. This was actually the root cause of #19 and #21, I believe.
        # However, we already have it loaded, at `kmsu2`, because Kancolle is stupid.
        kmsu = kmsu2
        # Bump the other ship numbers down.
        for kanmusu in fleet.kanmusu:
            if kanmusu == kmsu:
                pass
            elif kanmusu.fleet_position is None:
                print("Unknown error - fleet position is None, yet it's still in the fleet?!?")
                print("ID - {}".format(kanmusu.id))
                # Fix fleet position to be 5, at least temporarily.
                kanmusu.fleet_position = 5
            elif kanmusu.fleet_position > current_ship_pos:
                kanmusu.fleet_position -= 1
                db.session.add(kanmusu)
        # Remove fleet position
        kmsu.fleet_position = None
        # Remove from fleet
        fleet.kanmusu.remove(kmsu)
        # Add to session
        db.session.add(fleet)
        db.session.add(kmsu)
        db.session.commit()
        return svdata({})

    print(ship_pos, current_ship_pos)
    # Change fleet position of kanmusu 1.
    kmsu.fleet_position = ship_pos
    # Change fleet position of kanmusu 2, if applicable.
    if kmsu2:
        kmsu2.fleet_position = current_ship_pos
    db.session.add(kmsu, kmsu2)
    db.session.commit()
    return svdata({})


@api_actions.route('/api_req_quest/start', methods=['GET', 'POST'])
# Start quest
def queststart():
    admiral = get_token_admiral_or_error()
    quest_id = request.values.get("api_quest_id")
    AdmiralHelper.activate_quest(quest_id, admiral)
    _QuestHelper.update_quest_progress(quest_id, admiral)
    return svdata({'api_result_msg': 'ok', 'api_result': 1})


@api_actions.route('/api_req_quest/stop', methods=['GET', 'POST'])
# Stop quest
def queststop():
    admiral = get_token_admiral_or_error()
    quest_id = request.values.get("api_quest_id")
    AdmiralHelper.deactivate_quest(quest_id, admiral)
    return svdata({'api_result_msg': 'ok', 'api_result': 1})


@api_actions.route('/api_req_quest/agclearitemget', methods=['GET', 'POST'])
# Complete quest
def clearitemget():
    admiral = get_token_admiral_or_error()
    quest_id = request.values.get("api_quest_id")
    data = _QuestHelper.complete_quest(admiral, quest_id)
    return svdata(data)


api_user = Blueprint('api_user', __name__)
prepare_api_blueprint(api_user)


@api_user.route("/api_get_member/charge", methods=["GET", "POST"])
def resupply():
    # Get the ships. Misleading name of the year candidate.
    ships = request.values.get("api_id_items")
    ships = ships.split(',')
    # New dict for api_ships
    api_ships = {}
    for ship_id in ships:
        ship = Kanmusu.query.filter(Admiral.id == g.admiral.id, Kanmusu.number == ship_id).first_or_404()
        # Assertion for autocompletion in pycharm
        assert isinstance(ship, Kanmusu)
        # Calculate requirements.
        # Follows this formula: how many bars they use x 10% x their fuel/ammo cost


# @api_user.route('/api_get_member/material', methods=['GET', 'POST'])
# def material():
#    """Resources such as fuel, ammo, etc..."""
#    admiral = get_token_admiral_or_error()
#    return svdata(gamestart.get_admiral_resources_api_data(admiral))


# api_user.route('/api_get_member/mapinfo', methods=['GET', 'POST'])
# def mapinfo():
#    return svdata(_AdmiralHelper.get_admiral_sorties())


@api_user.route('/api_get_member/questlist', methods=['GET', 'POST'])
# My god, he rebuilds the questlist every time you (de)activate a quest...
def questlist():
    import math
    page_number = request.values.get('api_page_no', None)
    data = {}
    admiral = get_token_admiral_or_error()
    questlist = QuestHelper.get_questlist_ordered(admiral)
    data['api_count'] = len(questlist)
    data['api_page_count'] = int(math.ceil(data['api_count'] / 5))
    data["api_disp_page"] = int(page_number)
    data["api_list"] = []
    for admiral_quest, quest in questlist:
        data["api_list"].append({
            "api_no": quest.id, "api_category": quest.category, "api_type": quest.frequency,
            "api_state": admiral_quest.state, "api_title": quest.title, "api_detail": quest.detail,
            "api_get_material": quest.reward.to_list(), "api_bonus_flag": quest.bonus_flag,
            "api_progress_flag": admiral_quest.progress, "api_invalid_flag": quest.invalid_flag
        })
    return svdata(data)


@api_user.route('/api_get_member/ship3', methods=['GET', 'POST'])
# Heh
def ship3():
    admiral = g.admiral
    # No idea.
    # spi_sort_order = request.values.get('spi_sort_order')
    # spi_sort_order = request.values.get('api_sort_key')
    admiral_ship_id = request.values.get('api_shipid')
    data = {
        "api_ship_data": [_ShipHelper.get_admiral_ship_api_data(
            admiral_ship_id)], "api_deck_data": AdmiralHelper.get_admiral_deck_api_data(
            admiral), "api_slot_data": _ItemHelper.get_slottype_list(admiral=admiral)
    }
    return svdata(data)


@api_user.route('/api_get_member/test', methods=['GET', 'POST'])
def test():
    return svdata({})


# Generic routes for anything not implemented.

@api_user.route('/api_req_init/<path:path>', methods=['GET', 'POST'])
def misc(path):
    return svdata({'api_result_msg': '申し訳ありませんがブラウザを再起動し再ログインしてください。', 'api_result': 201})


@api_user.route('/api_get_member/<path:path>', methods=['GET', 'POST'])
def misc2(path):
    return svdata({'api_result_msg': '申し訳ありませんがブラウザを再起動し再ログインしてください。', 'api_result': 201})
