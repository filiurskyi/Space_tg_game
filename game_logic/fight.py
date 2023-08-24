from app.database import db_read_int, db_read_dict, db_write_int, db_write_dict, db_read_details, db_read_enemies_attributes
from asyncio import sleep, gather
from random import randint
from game_logic.space_map import *
from game_logic.mechanics import get_player_information, jump_home


async def init_fight(user_id, enemy_id):
    stats = await get_player_information(user_id, "location", "max_health", "current_health", "level", "ship_slots")
    # print(stats)
    location = int(stats[0])  # to use in possible location debuffs
    max_health = int(stats[1])
    current_health = int(stats[2])
    level = int(stats[3])
    ship_slots = {key: value for key, value in stats[4].items() if value != ""}
    print(ship_slots)
    # print(f"location={location} max_health={max_health} current_health={current_health}, level={level}")

    player_dmg = await get_player_dmg(ship_slots)
    player_shield = await get_player_shield(ship_slots)
    player_armor = await get_player_armor(ship_slots)

    # dmg calculation

    enemy_stats = await get_enemy_fight_stats(enemy_id)
    print("enemy stats", enemy_stats)
    en_hp = enemy_stats.get("health")
    en_dmg = enemy_stats.get("damage")
    en_arm = enemy_stats.get("armor")
    en_shld = enemy_stats.get("shields")

    battle_log = ""

    while current_health > 0 and en_hp > 0:
        print("entered loop")
        en_hp = (en_hp + en_shld + en_arm) - player_dmg
        print(en_hp)
        if en_hp < 0:
            break
        battle_log += f"Enemy HP: {en_hp}\n"
        current_health = (current_health + player_shield +
                          player_armor) - en_dmg
        print(current_health)
        battle_log += f"Your HP: {current_health}\n"
    print(battle_log)
    if current_health > 0:
        loot = await get_fight_drop(user_id, enemy_id)
        battle_log += f"You looted: {loot}\n"
        return battle_log
    else:
        await jump_home(user_id)
        return "you are dead"


async def get_player_dmg(ship_slots) -> int:
    weapons = {key: value for key, value in ship_slots.items()
               if key.startswith("weapons")}
    # print("wep", weapons)
    player_dmg = 0
    if not weapons is None:
        for weapon in weapons.values():
            it_shortname = f"\"{weapon}\""
            it_effects = await db_read_details("items", it_shortname, "effects", "it_shortname")

            crit_multiplier = 1.5
            player_dmg += int(randint(it_effects.get("damage_min"),
                              it_effects.get("damage_max"))*crit_multiplier)
    return player_dmg
    # print(it_shortname)
    # print(f"Found weapon equipped: {weapon}, stats: {it_effects}")
    # print(player_dmg)


async def get_player_shield(ship_slots) -> int:
    shields = {key: value for key, value in ship_slots.items() if key.startswith(
        "shield")}  # possible to have ship with multiple shield slots
    # print("shld", shields)
    player_shield = 0
    if not shields is None:
        for shield in shields.values():
            it_shortname = f"\"{shield}\""
            it_effects = await db_read_details("items", it_shortname, "effects", "it_shortname")
            player_shield += int((it_effects.get("shield")))
    return player_shield


async def get_player_armor(ship_slots) -> int:
    armors = {key: value for key, value in ship_slots.items() if key.startswith(
        "armor")}  # possible to have ship with multiple armor slots
    # print("arm", armors)
    player_armor = 0
    if not armors is None:
        for armor in armors.values():
            it_shortname = f"\"{armor}\""
            it_effects = await db_read_details("items", it_shortname, "effects", "it_shortname")
            player_armor += int((it_effects.get("armor")))
    return player_armor


async def get_enemy_fight_stats(enemy_id):
    enemy = f"\"{enemy_id}\""
    stats = await db_read_details("enemies", enemy, "stats", "en_shortname")
    return stats


async def get_fight_drop(user_id, enemy_id):
    loot_log = ""
    return loot_log
