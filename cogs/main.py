# main.py
"""Contains error handling and the help and about commands"""

from typing import List, Optional

import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands
from howlongtobeatpy import HowLongToBeat, HowLongToBeatEntry


class PaginatorButton(discord.ui.Button):
    """Paginator button"""
    def __init__(self, custom_id: str, label: str, disabled: bool = False, emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=discord.ButtonStyle.grey, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.custom_id == 'prev':
            self.view.active_page -= 1
            if self.view.active_page == 1: self.disabled = True
            for child in self.view.children:
                if child.custom_id == 'next':
                    child.disabled = False
                    break
        elif self.custom_id == 'next':
            self.view.active_page += 1
            if self.view.active_page == len(self.view.pages): self.disabled = True
            for child in self.view.children:
                if child.custom_id == 'prev':
                    child.disabled = False
                    break
        else:
            return
        for child in self.view.children:
            if child.custom_id == 'pages':
                child.label = f'{self.view.active_page}/{len(self.view.pages)}'
                break
        await interaction.response.edit_message(embed=self.view.pages[self.view.active_page-1], view=self.view)


class PaginatorView(discord.ui.View):
    """Paginator view with three buttons (previous, page count, next).

    Also needs the interaction of the response with the view, so do AbortView.interaction = await ctx.respond('foo').

    Returns
    -------
    'timeout' on timeout.
    None if nothing happened yet.
    """
    def __init__(self, ctx: discord.ApplicationContext, pages: List[discord.Embed],
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=300)
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.pages = pages
        self.active_page = 1
        self.add_item(PaginatorButton(custom_id='prev', label='◀', disabled=True, emoji=None))
        self.add_item(discord.ui.Button(custom_id="pages", style=discord.ButtonStyle.grey, disabled=True,
                                        label=f'1/{len(self.pages)}'))
        self.add_item(PaginatorButton(custom_id='next', label='▶', emoji=None))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message('You are not allowed to use this interaction', ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.value = 'timeout'
        self.stop()


class MainCog(commands.Cog):
    """Cog with events and help and about commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Commands
    cmd_search = SlashCommandGroup("search", "Search commands")
    @cmd_search.command(name='game', description='Look up a game on HLTB')
    async def search_game(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, 'Name or part of the name of the game'),
        ) -> None:
        """Search command"""
        await ctx.defer()
        results = await HowLongToBeat().async_search(name)
        if not results:
            await ctx.respond('No game found for that search term, sorry.')
            return
        embeds = []
        for result in results:
            embed = await embed_search(len(results), result)
            embeds.append(embed)
        if len(embeds) > 1:
            view = PaginatorView(ctx, embeds)
            message = await ctx.respond(embed=embeds[0], view=view)
            view.interaction = message
            await view.wait()
            await message.edit(view=None)
        else:
            await ctx.respond(embed=embed)

     # Events
    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception) -> None:
        """Runs when an error occurs and handles them accordingly.
        Interesting errors get written to the database for further review.
        """
        async def send_error() -> None:
            """Sends error message as embed"""
            embed = discord.Embed(title='An error occured')
            command_name = f'{ctx.command.full_parent_name} {ctx.command.name}'.strip()
            embed.add_field(name='Command', value=f'`{command_name}`', inline=False)
            embed.add_field(name='Error', value=f'```py\n{error}\n```', inline=False)
            await ctx.respond(embed=embed, ephemeral=True)

        error = getattr(error, 'original', error)
        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return
        elif isinstance(error, commands.DisabledCommand):
            await ctx.respond(f'Command `{ctx.command.qualified_name}` is temporarily disabled.', ephemeral=True)
        elif isinstance(error, (commands.MissingPermissions, commands.MissingRequiredArgument,
                                commands.TooManyArguments, commands.BadArgument)):
            await send_error()
        elif isinstance(error, commands.BotMissingPermissions):
            if 'send_messages' in error.missing_permissions:
                return
            if 'embed_links' in error.missing_perms:
                await ctx.respond(error, ephemeral=True)
            else:
                await send_error()
        else:
            await send_error()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Fires when bot has finished starting"""
        startup_info = f'{self.bot.user.name} has connected to Discord!'
        print(startup_info)


# Initialization
def setup(bot):
    bot.add_cog(MainCog(bot))


# --- Embeds ---
async def embed_search(result_amount: int, result: HowLongToBeatEntry) -> discord.Embed:
    """Search embed"""
    playtimes = ''
    if result.gameplay_main != -1 and result.gameplay_main_label is not None and result.gameplay_main_unit is not None:
        playtimes = (
            f'{playtimes}\n'
            f'🔹 **{result.gameplay_main_label}**: {result.gameplay_main} {result.gameplay_main_unit.lower()}'
        )
    if (result.gameplay_main_extra != -1 and result.gameplay_main_extra_label is not None
        and result.gameplay_main_extra_unit is not None):
        playtimes = (
            f'{playtimes}\n'
            f'🔹 **{result.gameplay_main_extra_label}**: {result.gameplay_main_extra} '
            f'{result.gameplay_main_extra_unit.lower()}'
        )
    if (result.gameplay_completionist != -1 and result.gameplay_completionist_label is not None
        and result.gameplay_completionist_unit is not None):
        playtimes = (
            f'{playtimes}\n'
            f'🔹 **{result.gameplay_completionist_label}**: {result.gameplay_completionist} '
            f'{result.gameplay_completionist_unit.lower()}'
        )
    playtimes = playtimes.strip()
    if playtimes == '': playtimes = '🔹 N/A'

    embed = discord.Embed(
        title = result.game_name,
    )
    embed.set_footer(text=f'Your search found {result_amount} games.')
    embed.set_thumbnail(url=f'https://howlongtobeat.com{result.game_image_url}')
    embed.add_field(name='How long to beat', value=playtimes, inline=False)
    embed.add_field(name='Link', value=f'🔹 {result.game_web_link}', inline=False)
    return embed