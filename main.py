import hikari
import lightbulb
import yaml

with open("config.yaml") as cfg:
    config = yaml.safe_load(cfg)

if __name__ == "__main__":
    bot = lightbulb.BotApp(token=config["token"])
    bot.load_extensions_from("plugins")
    bot.run()
