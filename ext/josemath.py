#!/usr/bin/env python3

import discord
import asyncio
import sys
sys.path.append("..")
import jauxiliar as jaux
import joseerror as je
import joseconfig as jconfig

import wolframalpha
wac = wolframalpha.Client(jconfig.WOLFRAMALPHA_APP_ID)

import pyowm
owm = pyowm.OWM(jconfig.OWM_APIKEY)

class JoseMath(jaux.Auxiliar):
    def __init__(self, cl):
        jaux.Auxiliar.__init__(self, cl)
        self.wac = wac
        self.owm = owm

    async def ext_load(self):
        return True, ''

    async def ext_unload(self):
        return True, ''

    async def c_wolframalpha(self, message, args, cxt):
        '''`!wolframalpha terms` - make a request to Wolfram|Alpha
        **ratelimit GLOBAL: 2 chamadas por hora**'''
        if len(args) < 2:
            await cxt.say(self.c_wolframalpha.__doc__)
            return

        term_to_wolfram = ' '.join(args[1:])

        res = self.wac.query(term_to_wolfram)
        if getattr(res, 'results', False):
            try:
                response_wolfram = next(res.results).text
            except StopIteration:
                await cxt.say(":warning: Erro tentando pegar o texto da resposta :warning:")
                return
            await cxt.say("%s:\n%s" % (term_to_wolfram, self.codeblock("", response_wolfram)))
        else:
            await cxt.say(":cyclone: Sem resposta :cyclone:")
            return

    async def c_wa(self, message, args, cxt):
        '''`!wa terms` - alias para `!wolframalpha`'''
        await self.c_wolframalpha(message, args, cxt)

    async def c_temperature(self, message, args, cxt):
        '''`!temperature location` - Temperatura de um local, usando OpenWeatherMap
        mostra tanto em Celsius quanto em Fahrenheit
        **ratelimit GLOBAL: 60 chamadas / minuto**'''
        if len(args) < 2:
            await cxt.say(self.c_temperature.__doc__)
            return

        location = ' '.join(args[1:])

        try:
            observation = owm.weather_at_place(location)
        except:
            await cxt.say("Erro tentando conseguir a temperatura para esse local")
            return
        w = observation.get_weather()

        tempcelsius = w.get_temperature("celsius")
        tempfahren = w.get_temperature("fahrenheit")

        celsiusnow = tempcelsius['temp']
        fahnow = tempfahren['temp']

        await cxt.say("%s °C, %s °F" % (celsiusnow, fahnow))

    async def c_temp(self, message, args, cxt):
        '''`!temp location` - alias para `!temperature`'''
        await self.c_temperature(message, args, cxt)

    async def c_therm(self, message, args, cxt):
        '''`!therm location` - alias para `!temperature`'''
        await self.c_temperature(message, args, cxt)

    def lewd(self, n):
        num = 3
        t = 0
        while t != n:
            lewd = num ** 2 - 2
            for a in range(2, lewd):
                if lewd % a == 0:
                    break
            else:
                yield num
                t += 1
            num += 6

    async def c_lewd(self, message, args, cxt):
        '''`!lewd n` - shows the `n` lewd numbers'''
        if len(args) < 2:
            await cxt.say(self.c_lewd.__doc__)

        try:
            n = int(args[1])
        except Exception as e:
            await cxt.say("Error parsing arguments: %r" % e)
            return

        if n > 100:
            await cxt.say("nope")
            return

        await cxt.say(self.codeblock("", list(self.lewd(n))))
