from aiogram.types import Message
from app.database import db_read_details, db_write_int, db_read_int, db_read_dict, db_read_full_name
import asyncio
from random import randint
import game_logic.inventory as invent
import game_logic.mechanics as m
from game_logic.space_map import *
from game_logic.states import State
import keyboards.main_kb as kb
from emojis import *


async def init_fight(message: Message, enemy_id, state: State, with_timer=True):
    user_id = message.from_user.id
    state_data = await state.get_data()
    keyboard = await kb.keyboard_selector(state)
    await state.set_state(State.fighting)
    stats = await m.get_player_information(user_id, "location", "max_health", "current_health", "level", "ship_slots")
    location = int(stats[0])  # to use in possible location debuffs
    max_health = int(stats[1])
    current_health = int(stats[2])
    level = int(stats[3])  # for escaping calc
    ship_slots = {key: value for key, value in stats[4].items() if value != ""}

    player_dmg = await get_player_dmg(ship_slots)
    player_shield = 0  # await get_player_shield(ship_slots)
    player_armor = await get_player_armor(ship_slots)

    # dmg calculation
    enemy_stats = await get_enemy_fight_stats(enemy_id)
    en_name = await db_read_details("enemies", enemy_id, "en_name", "en_shortname")
    en_hp = enemy_stats.get("health")
    en_dmg = enemy_stats.get("damage")
    en_arm = enemy_stats.get("armor")
    en_shld = 0  # enemy_stats.get("shields")
    print(f"\nFIGHT BEGIN with {en_name}\npl_hp={current_health}, pl_dmg={player_dmg}\nen_hp={en_hp}, en_dmg={en_dmg}")
    # await message.answer("You are fighting against {en_name}.\nYor enemy has HP:{en_hp}, DMG:{en_dmg}", reply_markup=keyboard)
    rounds_counter = 0
    while current_health > 0 and en_hp > 0:
        rounds_counter += 1
        # player hit enemy
        print("looping..")
        eff_player_dmg = max(player_dmg - en_shld, 0)
        en_hp = max(0, en_hp - eff_player_dmg)
        if with_timer:
            await timer()
        if en_hp <= 0:  # player win
            drop_text = await get_fight_drop(user_id, enemy_id)
            win_text = "\n\nYou live to die another day..\n\nYou looted:\n" + drop_text
            await state.clear()
            await state.set_state(State.gps_state)
            gps = await m.get_location(message.from_user.id)
            await state.update_data(gps_state=gps)
            await state.set_state(State.job)
            await state.update_data(job=f"Won after fight with {enemy_id}")
            print("player won with left hp:", current_health)
            return "win", win_text, rounds_counter

        # enemy hit player
        eff_en_dmg = max(en_dmg - player_shield, 0)
        current_health = max(0, current_health - eff_en_dmg)
        if current_health <= 0:  # enemy win
            dead_text = "\nYou lost your glorious figt, cap. Yor enemy had {en_hp}HP left.\nYour ship will be floating in space indefinitely".format(
                en_hp=en_hp)
            await message.answer(dead_text, reply_markup=keyboard)
            loose_text = "\n\nYour ship has been luckily picked up by some stragers. They dropped out from hauler nearly deat at Ringworld."
            # jump_home_task = await m.player_dead(user_id)
            print("player lost with enemy left hp:", en_hp)
            return "loose", loose_text
        await db_write_int("players", user_id, "current_health", current_health)
        print("Round : ", rounds_counter)
        print("pl_hp = ", current_health, "en_hp = ", en_hp)


async def get_player_dmg(ship_slots) -> int:
    weapons = {key: value for key, value in ship_slots.items()
               if key.startswith("weapon_")}
    player_dmg = 0
    if not weapons is None:
        for weapon in weapons.values():
            if weapon == "":
                continue
            it_shortname = f"\"{weapon}\""
            if it_shortname == "":
                continue
            it_effects = await db_read_details("items", it_shortname, "effects", "it_shortname")

            crit_multiplier = 1.5
            player_dmg += int(randint(it_effects.get("damage_min"),
                              it_effects.get("damage_max"))*crit_multiplier)
    return player_dmg


async def get_player_shield(ship_slots) -> int:
    shields = {key: value for key, value in ship_slots.items() if key.startswith(
        "shield")}  # possible to have ship with multiple shield slots
    # print("shld", shields)
    player_shield = 0
    if not shields is None:
        for shield in shields.values():
            if shield == "":
                continue
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
            if armor == "":
                continue
            it_shortname = f"\"{armor}\""
            it_effects = await db_read_details("items", it_shortname, "effects", "it_shortname")
            player_armor += int((it_effects.get("armor")))
    return player_armor


async def get_enemy_fight_stats(en_shortname):
    # enemy = f"\"{en_shortname}\""
    enemy = en_shortname
    stats = await db_read_details("enemies", enemy, "stats", "en_shortname")
    return stats


async def get_fight_drop(user_id, en_shortname):
    # en_shortname = f"\"{en_shortname}\""
    drop = []
    en_drop = await db_read_details("enemies", en_shortname, "en_drop", "en_shortname")

    # credits
    got_credits = en_drop.get("credits")
    credits_output = await invent.change_pl_credits(user_id, got_credits)
    drop.append(credits_output[1])
    # exp
    exp = en_drop.get("exp")
    drop.append("{bar_chart}Exploration Data : {exp}".format(
        exp=exp, bar_chart=bar_chart))
    await invent.add_pl_exp(user_id, exp)

    # items
    en_drop_items = {key: value for key, value in en_drop.items() if key.startswith(
        "it_name_")}
    # print("en_drop_items", en_drop_items)
    # {'it_name_1': {'droprate': 0.5, 'scrap_metal': 1}}
    for drop_only_items in en_drop_items.values():
        try:
            droprate = float(drop_only_items.get("droprate"))
        except:
            droprate = 1  # defauld drop rate ist 100%
        # print("drop_only_items ", drop_only_items)
        if await m.roll_chance(droprate):
            # print("droprate ", droprate)
            only_items = {key: value for key,
                          value in drop_only_items.items() if key != "droprate"}
            for it_shortname, count in only_items.items():
                it_shortname = f"\"{it_shortname}\""
                it_name = await db_read_full_name("items", it_shortname, "it_name", "it_shortname")
                # with drop chance {droprate}."
                text = f"Dropped {it_name} (x{count})"
                await invent.add_pl_items(user_id, it_shortname[1:-1], count)
                drop.append(text)

    # materials
    old_materials = await db_read_int("players", user_id, "pl_materials")
    en_drop_materials = {key: value for key, value in en_drop.items() if key.startswith(
        "mt_name_")}
    # print("en_drop_materials", en_drop_materials)
    # {'mt_name_1': {'droprate': 0.5, 'scrap_metal': 1}}
    for drop_only_materials in en_drop_materials.values():
        try:
            droprate = float(drop_only_materials.get("droprate"))
        except:
            droprate = 1  # defauld drop rate ist 100%
        if await m.roll_chance(droprate):
            # print("droprate ", droprate)
            only_materials = {key: value for key,
                              value in drop_only_materials.items() if key != "droprate"}
            # print("only_materials ", only_materials)
            for mt_shortname, count in only_materials.items():
                mt_shortname = f"\"{mt_shortname}\""
                mt_name = await db_read_full_name("materials", mt_shortname, "mt_name", "mt_shortname")
                # with drop chance {droprate}."
                text = f"Dropped {mt_name} (x{count})"
                await invent.add_pl_materials(user_id, mt_shortname[1:-1], count)
                drop.append(text)
    # print("drop", drop)

    # print(old_materials)

    return "\n".join(drop)


async def timer():
    print("awaiting timer")
    await asyncio.sleep(2)
    print("timer ended")


async def engaging_enemy_choice(user_id, en_shortname):
    en_dmg = await get_enemy_fight_stats(en_shortname)
    en_dmg = en_dmg["damage"]
    pl_health = await m.get_player_information(user_id, "max_health")
    if pl_health[0] / en_dmg < 2:
        return True
    else:
        return False
