from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from game import Game, MIN_PLAYERS, MAX_PLAYERS


def lobby_keyboard(game: Game) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🙋 Вступить в игру", callback_data="join")],
    ]
    if len(game.players) >= MIN_PLAYERS and len(game.players) <= MAX_PLAYERS:
        rows.append([InlineKeyboardButton(text="🚀 Начать игру!", callback_data="start_game")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def team_selection_keyboard(game: Game) -> InlineKeyboardMarkup:
    rows = []
    for player in game.players:
        selected = player.user_id in game.proposed_team
        icon = "✅" if selected else "⬜"
        rows.append([InlineKeyboardButton(
            text=f"{icon} {player.name}",
            callback_data=f"pick_{player.user_id}",
        )])
    selected_count = len(game.proposed_team)
    if selected_count == game.team_size:
        rows.append([InlineKeyboardButton(
            text=f"✔️ Подтвердить команду ({selected_count}/{game.team_size})",
            callback_data="confirm_team",
        )])
    else:
        rows.append([InlineKeyboardButton(
            text=f"Выбрано: {selected_count}/{game.team_size}",
            callback_data="confirm_team_disabled",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def team_vote_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ За", callback_data="vote_team_za"),
        InlineKeyboardButton(text="❌ Против", callback_data="vote_team_protiv"),
    ]])


def mission_vote_keyboard(is_spy: bool) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text="✅ Успех", callback_data="vote_mission_uspeh")]
    if is_spy:
        buttons.append(InlineKeyboardButton(text="💀 Провал", callback_data="vote_mission_proval"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])
