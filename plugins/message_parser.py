import hikari
import lightbulb
import db
import re
import asyncio
from thefuzz.fuzz import token_sort_ratio
from thefuzz.process import extractOne
from main import config
from sqlite3 import OperationalError

plugin = lightbulb.Plugin("Message Parser")
plugin.add_checks(lightbulb.human_only)


async def generate_embed(cardset: str, card: str, footer: str = None):
    embed = hikari.embeds.Embed(
        title=await db.query(f'select trigger from {cardset} where trigger = "{card}"'),
        description=await db.query(
            f'select response from {cardset} where trigger = "{card}"'
        ),
    )
    embed.set_image(
        await db.query(f'select image from {cardset} where trigger = "{card}"')
    )
    embed.set_footer(footer)
    return embed


@plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message(event: hikari.GuildMessageCreateEvent) -> None:
    if (event.is_bot) or (not event.message.content):
        return

    for cardset in config["cardsets"]:
        cards = re.findall(
            f"{config['cardsets'][cardset]['delim_start']}(.*?){config['cardsets'][cardset]['delim_end']}",
            event.message.content,
        )

        if cards:
            components = event.app.rest.build_action_row()
            button_prev = components.add_button(1, "prev")
            button_next = components.add_button(1, "next")
            button_prev.set_label("Previous")
            button_next.set_label("Next")
            button_prev.add_to_container()
            button_next.add_to_container()

            try:
                triggers = await db.queryall(f"select trigger from {cardset}")
            except OperationalError as e:
                if str(e) == "attempt to write a readonly database":
                    triggers = await db.queryall_rw(f"select trigger from {cardset}")

            if not triggers:
                raise Exception(
                    "No triggers for this cardset! Please add some into the database."
                )
            match = extractOne(cards[0], triggers, scorer=token_sort_ratio)[0]

            response = await event.message.respond(
                embed=await generate_embed(
                    cardset,
                    match,
                    (f"Match 1 of {len(cards)}" if len(cards) > 1 else None),
                ),
                component=(components if len(cards) > 1 else None),
            )

            page = 1
            embed = response.embeds[0]
            if len(cards) > 1:

                def predicate(ievent: hikari.InteractionCreateEvent) -> bool:
                    return (
                        ievent.interaction.type
                        == hikari.InteractionType.MESSAGE_COMPONENT
                        and isinstance(ievent.interaction, hikari.ComponentInteraction)
                        and ievent.interaction.message.id == response.id
                    )

                while True:
                    try:
                        event = await event.app.wait_for(
                            hikari.InteractionCreateEvent,
                            timeout=60,
                            predicate=predicate,
                        )
                    except asyncio.TimeoutError:
                        embed.set_footer("Interaction has timed out.")
                        await response.edit(embed=embed, component=None)
                        return

                    assert isinstance(event.interaction, hikari.ComponentInteraction)

                    if event.interaction.custom_id == button_prev.custom_id:
                        page = page - 1 if page > 1 else 1
                    elif event.interaction.custom_id == button_next.custom_id:
                        page = page + 1 if page < len(cards) else len(cards)

                    match = extractOne(
                        cards[page - 1], triggers, scorer=token_sort_ratio
                    )[0]
                    embed = await generate_embed(
                        cardset, match, f"Match {page} of {len(cards)}"
                    )
                    await event.interaction.create_initial_response(
                        hikari.ResponseType.MESSAGE_UPDATE,
                        embed=embed,
                        component=components,
                    )


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
