from game_setup.discord_helper import client, TOKEN, send_message, is_from_channel


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    await send_message("all", "Murder Mystery bot is online.")
    await send_message("murder", "Murderers, your private chat is ready.")
    await send_message("healer", "Healers, your private chat is ready.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if is_from_channel(message, "murder"):
        print(f"Murderer chat message: {message.content}")

        if message.content.startswith("kill "):
            target = message.content.replace("kill ", "", 1)
            await message.channel.send(f"Kill target received: {target}")

    elif is_from_channel(message, "healer"):
        print(f"Healer chat message: {message.content}")

        if message.content.startswith("heal "):
            target = message.content.replace("heal ", "", 1)
            await message.channel.send(f"Heal target received: {target}")

    elif is_from_channel(message, "all"):
        print(f"All-player chat message: {message.content}")


client.run(TOKEN)