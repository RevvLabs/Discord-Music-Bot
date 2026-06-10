from utils.helper_function.embed_layout import build_basic_layout


def setup_done(text_mention: str, category_name: str) -> object:
    return build_basic_layout(
        description=(
            f"### Temp Setup Completed\n"
            f"Text channel set to : **{text_mention}**\n"
            f"Category restricted to : **{category_name}**\n\n"
            f"Users must be in a voice channel inside **{category_name}** for the bot to join."
        )
    )


def setup_cleared() -> object:
    return build_basic_layout(
        description="### Temp Setup Cleared\nThe temp setup has been cleared for this server."
    )


def current_setup(text_mention: str, category_name: str) -> object:
    return build_basic_layout(
        description=(
            f"### Current Temp Setup\n"
            f"Text channel : **{text_mention}**\n"
            f"Category : **{category_name}**"
        )
    )


def no_setup() -> object:
    return build_basic_layout(description="### No Temp Setup Found\nNo temp setup configured for this server.")


def conflict_setup() -> object:
    return build_basic_layout(
        description="### Conflict\n`/setup` is already active. Clear it with `/clearsetup` before using `/temp-setup`."
    )


def conflict_temp() -> object:
    return build_basic_layout(
        description="### Conflict\n`/temp-setup` is already active. Clear it with `/clear-tempsetup` before using `/setup`."
    )


def wrong_channel(channel_mention: str) -> object:
    return build_basic_layout(
        description=f"### Wrong Channel\nPlease use {channel_mention} to run bot commands."
    )


def wrong_category(category_name: str) -> object:
    return build_basic_layout(
        description=f"### Wrong Voice Channel\nYou must be in a voice channel inside the **{category_name}** category."
    )
