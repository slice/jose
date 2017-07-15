import logging
import asyncio
import time

import discord
import markovify
from discord.ext import commands

from .common import Cog

log = logging.getLogger(__name__)


def make_textmodel(texter):
    texter.model = markovify.NewlineText(texter.data, texter.chain_length)


async def make_texter(chain_length, data, texter_id):
    texter = Texter(data, texter_id, chain_length)
    await texter.fill()
    return texter


class Texter:
    """Texter - Main texter class.

    This class holds information about a markov chain generator.
    """
    def __init__(self, data, texter_id, chain_length=1, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.id = texter_id
        self.refcount = 1
        self.chain_length = chain_length
        self.loop = loop
        self.data = data
        self.model = None

    async def fill(self):
        """Fill a texter with its text model."""
        t_start = time.monotonic()

        future_textmodel = self.loop.run_in_executor(None, make_textmodel, self)
        await future_textmodel

        delta = round((time.monotonic() - t_start) * 1000, 2)
        log.info(f"Texter.fill: {delta}ms")

    def _sentence(self, char_limit):
        """Get a sentence from a initialized texter."""
        text = 'None'
        if char_limit is not None:
            text = self.model.make_short_sentence(char_limit)
        else:
            text = self.model.make_sentence()

        return text

    async def sentence(self, char_limit=None):
        """Get a sentence from a initialized texter."""
        if self.refcount <= 4:
            # max value refcount can be is 5
            self.refcount += 1

        res = None
        count = 0
        while res is None:
            if count > 3: break
            future_sentence = self.loop.run_in_executor(None, self._sentence, char_limit)
            res = await future_sentence
            count += 1

        return str(res)

    def clear(self):
        del self.model, self.data


class Speak(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.text_generators = {}

        self.coll_task = self.bot.loop.create_task(self.coll_task_func())

    async def coll_task_func(self):
        try:
            while True:
                await self.texter_collection()
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def texter_collection(self):
        """Free memory by collecting unused Texters."""
        amount = len(self.text_generators)
        if amount < 1:
            return

        t_start = time.monotonic()
        cleaned = 0

        for texter in list(self.text_generators.values()):
            if texter.refcount < 1:
                texter.clear()
                cleaned += 1
                del self.text_generators[texter.id]
            else:
                texter.refcount -= 1

        t_end = time.monotonic()

        if cleaned > 0:
            delta = round((t_end - t_start) * 1000, 2)
            log.info(f'{amount} -> {amount - cleaned} in {delta}ms')

    async def get_messages(self, guild, amount=2000):
        channel_id = await self.config.cfg_get(guild, 'speak_channel')
        channel = guild.get_channel(channel_id)
        if channel is None:
            channel = guild.default_channel

        try:
            messages = []
            async for message in channel.history(limit=amount):
                author = message.author
                if author == self.bot.user:
                    continue

                if author.bot:
                    continue

                messages.append(message.clean_content)
            return messages
        except discord.Forbidden:
            log.info(f'got Forbidden from {guild.id} when making message history')
            return ['None']

    async def get_messages_str(self, guild, amount=2000):
        m = await self.get_messages(guild, amount)
        return '\n'.join(m)

    async def new_texter(self, guild):
        guild_messages = await self.get_messages_str(guild)
        new_texter = await make_texter(1, guild_messages, guild.id)
        self.text_generators[guild.id] = new_texter

    async def get_texter(self, guild):
        if guild.id not in self.text_generators:
            await self.new_texter(guild)

        return self.text_generators[guild.id]

    async def make_sentence(self, ctx, char_limit=None):
        with ctx.typing():
            texter = await self.get_texter(ctx.guild)

        sentence = await texter.sentence(char_limit)
        return sentence

    @commands.command()
    @commands.is_owner()
    async def texclean(self, ctx, amount: int = 1):
        """Clean texters."""
        before = len(self.text_generators)
        t_start = time.monotonic()

        for i in range(amount):
            await self.texter_collection()

        after = len(self.text_generators)
        t_end = time.monotonic()

        delta = round((t_end - t_start) * 1000, 2)
        await ctx.send(f"`{before} => {after}, cleaned {before-after}, took {delta}ms`")

    @commands.command()
    @commands.is_owner()
    async def ntexter(self, ctx, guild_id: int = None):
        """Create a new texter for a guild, overwrites existing one"""
        if guild_id is None:
            guild_id = ctx.guild.id

        guild = self.bot.get_guild(guild_id)
        t1 = time.monotonic()
        await self.new_texter(guild)
        t2 = time.monotonic()
        delta = round((t2 - t1), 2)
        await ctx.send(f'Took {delta} seconds loading texter.')

    @commands.command(aliases=['spt'])
    @commands.guild_only()
    async def speaktrigger(self, ctx):
        """Force your Texter to say a sentence."""
        sentence = await self.make_sentence(ctx)
        await ctx.send(sentence)

    @commands.command(hidden=True)
    async def covfefe(self, ctx):
        """covfefe."""
        await ctx.send("Despite the constant negative press covfefe.")

    @commands.command(aliases=['jw'])
    @commands.guild_only()
    async def jwormhole(self, ctx):
        """lul wormhole"""
        res = await self.make_sentence(ctx)
        await ctx.send(f'<@127296623779774464> wormhole send {res}')

    @commands.command()
    @commands.guild_only()
    async def madlibs(self, ctx, *, inputstr: str):
        """Changes any "---" in the input to a 12-letter generated sentence"""

        inputstr = inputstr.replace('@everyone', '@\u200beveryone')
        inputstr = inputstr.replace('@here', '@\u200bhere')

        splitted = inputstr.split()
        if splitted.count('---') < 1:
            await ctx.send(":no_entry_sign: you can't just make josé say whatever you want! :no_entry_sign:")
            return

        if splitted.count('---') > 5:
            await ctx.send("thats a .......... lot")
            return

        res = []

        for word in splitted:
            if word == '---':
                res.append(await self.make_sentence(ctx, 12))
            else:
                res.append(word)

        await ctx.send(' '.join(res))

def setup(bot):
    bot.add_cog(Speak(bot))