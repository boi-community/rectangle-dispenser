import hikari
import lightbulb

import db
from main import config


class DuplicateTriggerException(Exception):
    pass


class InvalidTriggerException(Exception):
    pass


@lightbulb.Check
def check_authorized(context: lightbulb.Context) -> bool:
    return context.author.id in config["db_admins"]


plugin = lightbulb.Plugin("Commands")
plugin.add_checks(check_authorized)


@plugin.command
@lightbulb.option(
    "response", "[Optional] Extra response to this trigger", required=False
)
@lightbulb.option("image", "[Optional] URL of the image", required=False)
@lightbulb.option("trigger", "Text in brackets which triggers a response")
@lightbulb.option(
    "cardset", "Cardset to add a card to", choices=config["cardsets"].keys()
)
@lightbulb.command("add", "Add a trigger and response")
@lightbulb.implements(lightbulb.SlashCommand)
async def add(ctx: lightbulb.Context) -> None:
    await db.create_table(ctx.options.cardset, ("trigger", "image", "response"))
    if await db.query(
        f'SELECT trigger FROM {ctx.options.cardset} WHERE trigger = "{ctx.options.trigger}"'
    ):
        raise DuplicateTriggerException()
    await db.insert(
        ctx.options.cardset,
        "(?,?,?)",
        (ctx.options.trigger, ctx.options.image, ctx.options.response),
    )
    await ctx.respond(
        f"Success! I will respond to `{ctx.options.trigger}` in the {ctx.options.cardset} cardset with the provided image.",
        flags=hikari.MessageFlag.EPHEMERAL,
    )


@plugin.command
@lightbulb.option("trigger", "Trigger of response to delete")
@lightbulb.option(
    "cardset", "Cardset to delete a response from", choices=config["cardsets"].keys()
)
@lightbulb.command("delete", "Delete a trigger and response")
@lightbulb.implements(lightbulb.SlashCommand)
async def delete(ctx: lightbulb.Context) -> None:
    if not await db.query(
        f'SELECT trigger FROM {ctx.options.cardset} WHERE trigger = "{ctx.options.trigger}"'
    ):
        raise InvalidTriggerException()

    await db.remove(ctx.options.cardset, f'trigger = "{ctx.options.trigger}"')
    await ctx.respond(
        f'Success! I have removed "{ctx.options.trigger}" from the {ctx.options.cardset} cardset.',
        flags=hikari.MessageFlag.EPHEMERAL,
    )


@plugin.command
@lightbulb.option(
    "response", "[Optional] New extra response to this trigger", required=False
)
@lightbulb.option("image", "[Optional] New URL of the image", required=False)
@lightbulb.option("trigger", "Cardset to update a response in")
@lightbulb.option(
    "cardset", "Official or custom cardset", choices=config["cardsets"].keys()
)
@lightbulb.command("update", "Update a response")
@lightbulb.implements(lightbulb.SlashCommand)
async def update(ctx: lightbulb.Context) -> None:
    if not await db.query(
        f'SELECT trigger FROM {ctx.options.cardset} WHERE trigger = "{ctx.options.trigger}"'
    ):
        raise InvalidTriggerException()
    if ctx.options.response:
        await db.update(
            ctx.options.cardset,
            f'response = "{ctx.options.response}" where trigger = "{ctx.options.trigger}"',
        )
    if ctx.options.image:
        await db.update(
            ctx.options.cardset,
            f'image = "{ctx.options.image}" where trigger = "{ctx.options.trigger}"',
        )
    await ctx.respond(
        f'Success! I will respond to "{ctx.options.trigger}" in the {ctx.options.cardset} cardset with cardset with the provided image.',
        flags=hikari.MessageFlag.EPHEMERAL,
    )


@plugin.set_error_handler()
async def command_error_handler(event: lightbulb.CommandErrorEvent) -> bool:
    exception = event.exception.__cause__ or event.exception
    if isinstance(exception, lightbulb.CheckFailure):
        response = "You have insufficient permissions to perform this action."
    elif isinstance(exception, DuplicateTriggerException):
        response = "That trigger already exists in this cardset."
    elif isinstance(exception, InvalidTriggerException):
        response = "That trigger does not exist."
    else:
        response = (
            f"An unknown error occured trying to perform this action: {exception}"
        )
    await event.context.respond(response, flags=hikari.MessageFlag.EPHEMERAL)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
