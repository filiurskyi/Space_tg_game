from aiogram.fsm.state import State, StatesGroup


class State(StatesGroup):
    # outdated:
    # busy = State()
    # idling = State()  # idle in space
    admin = State()
    adm_add_item = State()

    settings_menu = State()
    settings_nickname = State()

    gps_state = State()
    job = State()
    travelling = State()
    docked = State()

    confirmation = State()

    fighting_choice = State()
    fighting = State()
    repairing = State()
    scanning = State()
    mining = State()

    item_selector = State()

    # under_attack = State()
    # running = State()
    # at_loc = State()


async def is_busy(state_data):
    try:
        travelling_data = state_data["job"]
        gps = state_data["gps_state"]
        busy = travelling_data == "Jumping Home" or travelling_data == "Travelling forward"
        return busy
    except:
        return None  # not busy because after bot restart no gps state and no travel state
