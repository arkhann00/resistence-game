from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from game import Game, Player, games, registered_users, bot_username, MIN_PLAYERS, MAX_PLAYERS
from keyboards import lobby_keyboard, team_selection_keyboard, team_vote_keyboard, mission_vote_keyboard

router = Router()

RULES_TEXT = (
    "📖 <b>Сопротивление — краткие правила</b>\n\n"
    "🎯 <b>Цель:</b> Сопротивление хочет выполнить 3 миссии, Шпионы — провалить 3.\n\n"
    "🔄 <b>Раунд:</b>\n"
    "1. Лидер выбирает команду для миссии\n"
    "2. Все голосуют «За» или «Против» команды\n"
    "3. Если команда одобрена — участники голосуют за исход миссии (в ЛС)\n"
    "4. Сопротивление всегда голосует «Успех», шпионы могут выбрать «Провал»\n\n"
    "⚠️ Если 5 команд подряд отклонены — шпионы побеждают!\n"
    "⚠️ В 4-й миссии (при 7+ игроках) нужно 2 карты провала для провала миссии.\n\n"
    "👥 <b>Игроков → Шпионов:</b> 5-6 → 2, 7-9 → 3, 10 → 4"
)


def mention(player: Player) -> str:
    return f'<a href="tg://user?id={player.user_id}">{player.name}</a>'


def lobby_text(game: Game) -> str:
    count = len(game.players)
    if game.players:
        names = "\n".join(f"  {i+1}. {p.name}" for i, p in enumerate(game.players))
    else:
        names = "  —"
    text = (
        f"🎮 <b>Сопротивление</b>\n\n"
        f"Игроки ({count}/{MAX_PLAYERS}):\n{names}\n\n"
    )
    if count < MIN_PLAYERS:
        text += f"Нужно ещё минимум {MIN_PLAYERS - count} игрок(ов) для старта."
    else:
        text += "✅ Можно начинать! Хост нажимает «Начать игру»."
    return text


def team_building_text(game: Game) -> str:
    return (
        f"📊 {game.scoreboard()}\n\n"
        f"⚔️ <b>Миссия {game.mission_number}</b> — команда из <b>{game.team_size}</b> чел.\n"
        f"🔄 Попытка {game.rejection_count + 1}/5\n\n"
        f"👑 Лидер: {mention(game.leader)}\n\n"
        f"{mention(game.leader)}, выбери {game.team_size} игрок(ов):"
    )


def team_vote_text(game: Game) -> str:
    team = ", ".join(mention(p) for p in game.team_members)
    voted = len(game.team_votes)
    return (
        f"📊 {game.scoreboard()}\n\n"
        f"⚔️ <b>Миссия {game.mission_number}</b> — попытка {game.rejection_count + 1}/5\n\n"
        f"👑 Лидер: {mention(game.leader)}\n"
        f"🎯 Команда: {team}\n\n"
        f"🗳 Голосование: {voted}/{game.n} проголосовали"
    )


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type == "private":
        registered_users.add(message.from_user.id)
        await message.answer(
            "👋 Привет! Ты зарегистрирован и можешь вступать в игры.\n\n"
            "Зайди в групповой чат и нажми <b>«Вступить в игру»</b>.",
            parse_mode="HTML",
        )
    else:
        await message.answer("Используй /newgame чтобы начать новую игру!")


@router.message(Command("newgame"))
async def cmd_newgame(message: Message):
    if message.chat.type == "private":
        await message.answer("Эту команду нужно использовать в групповом чате!")
        return

    chat_id = message.chat.id
    existing = games.get(chat_id)
    if existing and existing.phase != "game_over":
        await message.answer("⚠️ Игра уже идёт! Дождитесь её окончания.")
        return

    game = Game(chat_id=chat_id, host_id=message.from_user.id)
    games[chat_id] = game

    msg = await message.answer(lobby_text(game), reply_markup=lobby_keyboard(game), parse_mode="HTML")
    game.lobby_msg_id = msg.message_id


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.answer(RULES_TEXT, parse_mode="HTML")


@router.message(Command("endgame"))
async def cmd_endgame(message: Message):
    chat_id = message.chat.id
    game = games.get(chat_id)
    if not game or game.phase == "game_over":
        await message.answer("Нет активной игры.")
        return
    if message.from_user.id != game.host_id:
        await message.answer("Только хост может завершить игру.")
        return
    game.phase = "game_over"
    await message.answer("🛑 Игра принудительно завершена хостом.")
    games.pop(chat_id, None)


# ──────────────────────────────────────────────
# Lobby callbacks
# ──────────────────────────────────────────────

@router.callback_query(F.data == "join")
async def cb_join(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user
    game = games.get(chat_id)

    if not game:
        await callback.answer("Нет активной игры!")
        return
    if game.phase != "lobby":
        await callback.answer("Игра уже началась!")
        return
    if user.id not in registered_users:
        import game as _g
        uname = _g.bot_username
        hint = f"@{uname}" if uname else "боту"
        await callback.answer(
            f"Сначала напиши {hint} в личку и нажми /start, затем возвращайся!",
            show_alert=True,
        )
        return
    if game.get_player(user.id):
        await callback.answer("Ты уже в игре!")
        return
    if game.n >= MAX_PLAYERS:
        await callback.answer("Игра уже заполнена!")
        return

    game.players.append(Player(user_id=user.id, name=user.full_name))
    await callback.answer(f"✅ {user.full_name} вступил(а) в игру!")

    try:
        await callback.message.edit_text(
            lobby_text(game), reply_markup=lobby_keyboard(game), parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "start_game")
async def cb_start_game(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.phase != "lobby":
        await callback.answer("Нет игры для запуска!")
        return
    if callback.from_user.id != game.host_id:
        await callback.answer("Только хост может начать игру!")
        return
    if game.n < MIN_PLAYERS:
        await callback.answer(f"Нужно минимум {MIN_PLAYERS} игроков!")
        return

    await callback.answer()
    game.assign_roles()

    # Send private role messages
    failed: list[str] = []
    spy_names = ", ".join(p.name for p in game.spies)

    for player in game.players:
        try:
            if player.is_spy:
                text = (
                    "🕵️ <b>Ты — ШПИОН!</b>\n\n"
                    f"Твои сообщники: <b>{spy_names}</b>\n\n"
                    "Цель: провалить 3 миссии. Не раскрой себя!"
                )
            else:
                text = (
                    "🦸 <b>Ты — СОПРОТИВЛЕНИЕ!</b>\n\n"
                    "Цель: выполнить 3 миссии.\n"
                    "Вычисли шпионов и не бери их в команду!"
                )
            await bot.send_message(player.user_id, text, parse_mode="HTML")
        except TelegramForbiddenError:
            failed.append(player.name)

    await bot.send_message(chat_id, "🎮 <b>Игра началась!</b> Роли отправлены в личку.", parse_mode="HTML")

    if failed:
        await bot.send_message(
            chat_id,
            f"⚠️ Не удалось отправить роль игрокам: <b>{', '.join(failed)}</b>\n"
            "Им нужно написать боту /start в личку.",
            parse_mode="HTML",
        )

    await _start_team_building(bot, game)


# ──────────────────────────────────────────────
# Team building
# ──────────────────────────────────────────────

async def _start_team_building(bot: Bot, game: Game) -> None:
    game.phase = "team_building"
    game.proposed_team = []

    msg = await bot.send_message(
        game.chat_id,
        team_building_text(game),
        reply_markup=team_selection_keyboard(game),
        parse_mode="HTML",
    )
    game.lobby_msg_id = msg.message_id  # reuse to track active message


@router.callback_query(F.data.startswith("pick_"))
async def cb_pick_player(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.phase != "team_building":
        await callback.answer()
        return
    if callback.from_user.id != game.leader.user_id:
        await callback.answer("Только лидер выбирает команду!", show_alert=True)
        return

    target_id = int(callback.data[5:])

    if target_id in game.proposed_team:
        game.proposed_team.remove(target_id)
        p = game.get_player(target_id)
        await callback.answer(f"➖ {p.name} убран из команды")
    else:
        if len(game.proposed_team) >= game.team_size:
            await callback.answer(f"Уже выбрано {game.team_size} — сначала убери кого-нибудь!")
            return
        game.proposed_team.append(target_id)
        p = game.get_player(target_id)
        await callback.answer(f"➕ {p.name} добавлен в команду")

    try:
        await callback.message.edit_text(
            team_building_text(game),
            reply_markup=team_selection_keyboard(game),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "confirm_team_disabled")
async def cb_confirm_disabled(callback: CallbackQuery):
    game = games.get(callback.message.chat.id)
    if game:
        await callback.answer(f"Нужно выбрать ровно {game.team_size} игрок(ов)!")
    else:
        await callback.answer()


@router.callback_query(F.data == "confirm_team")
async def cb_confirm_team(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.phase != "team_building":
        await callback.answer()
        return
    if callback.from_user.id != game.leader.user_id:
        await callback.answer("Только лидер подтверждает команду!", show_alert=True)
        return
    if len(game.proposed_team) != game.team_size:
        await callback.answer(f"Нужно ровно {game.team_size} игрок(ов)!")
        return

    await callback.answer()
    game.phase = "team_voting"
    game.team_votes = {}

    try:
        await callback.message.edit_text(
            team_vote_text(game),
            reply_markup=team_vote_keyboard(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass


# ──────────────────────────────────────────────
# Team voting
# ──────────────────────────────────────────────

@router.callback_query(F.data.in_({"vote_team_za", "vote_team_protiv"}))
async def cb_vote_team(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.phase != "team_voting":
        await callback.answer()
        return

    player = game.get_player(callback.from_user.id)
    if not player:
        await callback.answer("Ты не в этой игре!")
        return
    if callback.from_user.id in game.team_votes:
        await callback.answer("Ты уже проголосовал!")
        return

    vote = callback.data == "vote_team_za"
    game.team_votes[callback.from_user.id] = vote
    await callback.answer("✅ За!" if vote else "❌ Против!")

    try:
        await callback.message.edit_text(
            team_vote_text(game),
            reply_markup=team_vote_keyboard(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass

    if len(game.team_votes) == game.n:
        await _resolve_team_vote(bot, game, callback.message)


async def _resolve_team_vote(bot: Bot, game: Game, message) -> None:
    za = sum(1 for v in game.team_votes.values() if v)
    protiv = game.n - za
    approved = za > protiv

    team = ", ".join(mention(p) for p in game.team_members)

    vote_lines = []
    for player in game.players:
        v = game.team_votes.get(player.user_id)
        vote_lines.append(f"  {player.name}: {'✅ За' if v else '❌ Против'}")

    verdict = "✅ ОДОБРЕНА" if approved else "❌ ОТКЛОНЕНА"

    result_text = (
        f"📊 {game.scoreboard()}\n\n"
        f"⚔️ <b>Миссия {game.mission_number}</b>\n\n"
        f"🎯 Команда: {team}\n\n"
        f"Голоса:\n" + "\n".join(vote_lines) + "\n\n"
        f"За: {za} | Против: {protiv}\n"
        f"Команда <b>{verdict}</b>"
    )

    try:
        await message.edit_text(result_text, parse_mode="HTML")
    except TelegramBadRequest:
        pass

    if approved:
        game.rejection_count = 0
        await _start_mission(bot, game)
    else:
        game.rejection_count += 1
        if game.rejection_count >= 5:
            await _game_over(bot, game, spies_win=True, reason="5 команд подряд были отклонены")
        else:
            game.advance_leader()
            await _start_team_building(bot, game)


# ──────────────────────────────────────────────
# Mission execution
# ──────────────────────────────────────────────

async def _start_mission(bot: Bot, game: Game) -> None:
    game.phase = "mission"
    game.mission_votes = {}

    team_names = ", ".join(p.name for p in game.team_members)
    two_fail_note = " (нужно 2 провала для провала миссии)" if game.needs_two_fails() else ""
    await bot.send_message(
        game.chat_id,
        f"🚀 <b>Миссия {game.mission_number} начинается!</b>{two_fail_note}\n\n"
        f"Команда: {team_names}\n\nУчастники получат голосование в личку.",
        parse_mode="HTML",
    )

    for player in game.team_members:
        try:
            await bot.send_message(
                player.user_id,
                f"⚔️ <b>Миссия {game.mission_number}</b>\n\nВыбери исход миссии:",
                reply_markup=mission_vote_keyboard(player.is_spy),
                parse_mode="HTML",
            )
        except TelegramForbiddenError:
            # Auto-success if can't DM (shouldn't happen in normal flow)
            game.mission_votes[player.user_id] = True

    # Check if all votes already collected (edge case)
    if len(game.mission_votes) == len(game.proposed_team):
        await _resolve_mission(bot, game)


@router.callback_query(F.data.in_({"vote_mission_uspeh", "vote_mission_proval"}))
async def cb_vote_mission(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    target_game: Game | None = None
    for g in games.values():
        if g.phase == "mission" and user_id in g.proposed_team:
            target_game = g
            break

    if not target_game:
        await callback.answer("Ты не участник текущей миссии!")
        return
    if user_id in target_game.mission_votes:
        await callback.answer("Ты уже проголосовал!")
        return

    vote = callback.data == "vote_mission_uspeh"
    target_game.mission_votes[user_id] = vote

    if vote:
        await callback.answer("✅ Голос принят: Успех")
    else:
        await callback.answer("💀 Голос принят: Провал")

    try:
        await callback.message.edit_text(
            f"⚔️ Миссия {target_game.mission_number}\n\n✅ Твой голос принят! Ожидаем остальных…"
        )
    except TelegramBadRequest:
        pass

    if len(target_game.mission_votes) == len(target_game.proposed_team):
        await _resolve_mission(bot, target_game)


async def _resolve_mission(bot: Bot, game: Game) -> None:
    succeeded = game.mission_succeeded()
    fail_count = sum(1 for v in game.mission_votes.values() if not v)

    game.mission_results.append(succeeded)

    if succeeded:
        game.successes += 1
        icon = "✅ УСПЕХ"
    else:
        game.failures += 1
        icon = "❌ ПРОВАЛ"

    note = ""
    if game.needs_two_fails():
        note = f" (нужно было 2 провала, получено: {fail_count})"

    await bot.send_message(
        game.chat_id,
        f"🏁 <b>Миссия {game.mission_number}: {icon}</b>{note}\n\n"
        f"📊 {game.scoreboard()}\n"
        f"Сопротивление: {game.successes} ✅  |  Шпионы: {game.failures} ❌",
        parse_mode="HTML",
    )

    if game.successes >= 3:
        await _game_over(bot, game, spies_win=False)
    elif game.failures >= 3:
        await _game_over(bot, game, spies_win=True)
    else:
        game.mission_number += 1
        game.advance_leader()
        await _start_team_building(bot, game)


# ──────────────────────────────────────────────
# Game over
# ──────────────────────────────────────────────

async def _game_over(bot: Bot, game: Game, spies_win: bool, reason: str = "") -> None:
    game.phase = "game_over"

    spy_names = ", ".join(p.name for p in game.spies)
    res_names = ", ".join(p.name for p in game.resistance)

    if spies_win:
        headline = "🕵️ <b>ШПИОНЫ ПОБЕДИЛИ!</b>"
    else:
        headline = "🦸 <b>СОПРОТИВЛЕНИЕ ПОБЕДИЛО!</b>"

    text = (
        f"{headline}\n\n"
        + (f"Причина: {reason}\n\n" if reason else "")
        + f"📊 {game.scoreboard()}\n\n"
        f"🕵️ Шпионы: <b>{spy_names}</b>\n"
        f"🦸 Сопротивление: <b>{res_names}</b>\n\n"
        "Новая игра: /newgame"
    )

    await bot.send_message(game.chat_id, text, parse_mode="HTML")
    games.pop(game.chat_id, None)
