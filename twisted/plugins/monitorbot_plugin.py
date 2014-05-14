from ConfigParser import ConfigParser

from twisted.application.service import IServiceMaker, Service
from twisted.internet.endpoints import clientFromString
from twisted.plugin import IPlugin
from twisted.python import usage, log
from zope.interface import implementer

from twisted.internet import inotify
from twisted.python import filepath

from monitor.bot import MonitorBotFactory

class MonitorBotService(Service):
	_bot = None

	def __init__(self, endpoint, channel, nickname, realname, path):
		self._endpoint = endpoint
		self._channel = channel
		self._nickname = nickname
		self._realname = realname
		self._path = path

	def startService(self):
		"""Construct a client & connect to server."""
		from twisted.internet import reactor

		"""Define callbacks."""
		def connected(bot):
			self._bot = bot

		def failure(err):
			log.err(err, _why='Could not connect to specified server.')
			reactor.stop()

		client = clientFromString(reactor, self._endpoint)
		factory = MonitorBotFactory(
			self._channel,
			self._nickname,
			self._realname
		)

		def fsnotify(ignored, filepath, mask):
			msg = "event %s on %s" % (', '.join(inotify.humanReadableMask(mask)), filepath)
			self._bot.msg(self._channel, msg)
			pass

		notifier = inotify.INotify()
		notifier.startReading()
		notifier.watch(filepath.FilePath(self._path), autoAdd=True, recursive=True, callbacks=[fsnotify])

		"""Attach defined callbacks."""
		return client.connect(factory).addCallbacks(connected, failure)

	def stopService(self):
		"""Disconnect."""
		if self._bot and self._bot.transport.connected:
			self._bot.transport.loseConnection()


class Options(usage.Options):
	optParameters = [
		['config', 'c', 'settings.ini', 'Configuration file.'],
	]


@implementer(IServiceMaker, IPlugin)
class BotServiceMaker(object):
	tapname = "monitorbot"
	description = "IRC bot that provides verbose monitoring of an fs path."
	options = Options

	def makeService(self, options):
		"""Read the config and construct the monitorbot service."""
		config = ConfigParser()
		config.read([options['config']])

		return MonitorBotService(
			endpoint=config.get('irc', 'endpoint'),
			channel=config.get('irc', 'channel'),
			nickname=config.get('irc', 'nickname'),
			realname=config.get('irc', 'realname'),
			path=config.get('fsmonitor', 'path'),
		)

# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = BotServiceMaker()
