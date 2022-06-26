import hikari
import lightbulb
import db
import re
from thefuzz.fuzz import token_sort_ratio
from thefuzz.process import extractOne
from main import config

plugin = lightbulb.Plugin("Message Parser")
plugin.add_checks(lightbulb.human_only)


@plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message(event: hikari.GuildMessageCreateEvent) -> None:
    if event.is_bot:
        return
    for cardset in config["cardsets"]:
        for string in re.findall(
            f"{config['cardsets'][cardset]['delim_start']}(.*?){config['cardsets'][cardset]['delim_end']}",
            event.message.content,
        ):
            triggers = await db.queryall(f"select trigger from {cardset}")
            if not triggers:
                raise Exception(
                    "No triggers for this cardset! Please add some into the database."
                )
            match = extractOne(string, triggers, scorer=token_sort_ratio)[0]

            response_embed = hikari.embeds.Embed(
                title=match,
                description=await db.query(
                    f'select response from {cardset} where trigger = "{match}"'
                ),
            )
            response_embed.set_image(
                await db.query(f'select image from {cardset} where trigger = "{match}"')
            )
            await event.message.respond(embed=response_embed)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
