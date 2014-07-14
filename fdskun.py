# -*- coding: utf-8 -*-

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import usage, log
from twisted.internet import inotify
from twisted.python import filepath
from ConfigParser import ConfigParser

import time, sys

class MonitorBot(irc.IRCClient):
	"""A (FTP)-FileSystem Monitoring IRC bot."""

	def __init__(self, nickname):
		self.nickname = nickname

	def connectionMade(self):
		irc.IRCClient.connectionMade(self)
		print("[connected at %s]" % time.asctime(time.localtime(time.time())))

	def connectionLost(self, reason):
		irc.IRCClient.connectionLost(self, reason)
		print("[disconnected at %s]" % time.asctime(time.localtime(time.time())))

	# callbacks for events
	def signedOn(self):
		"""Called when bot has succesfully signed on to server."""
		self.join(self.factory.channel)

	def joined(self, channel):
		"""This will get called when the bot joins the channel."""
		print("[I have joined %s]" % channel)

	def privmsg(self, user, channel, msg):
		"""This will get called when the bot receives a message."""
		self.quit()
		pass

class MonitorBotFactory(protocol.ClientFactory):
	"""A factory for MonitorBots.

	A new protocol instance will be created each time we connect to the server.
	"""

	def __init__(self, nickname, channel, fsmon):
		self.nickname = nickname
		self.channel = channel
		self.fsmon = fsmon

	def buildProtocol(self, addr):
		p = MonitorBot(self.nickname)
		self.fsmon.setBot(p)
		p.factory = self
		return p

	def clientConnectionLost(self, connector, reason):
		"""If we get disconnected, reconnect to server."""
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print "connection failed:", reason
		reactor.stop()

class Options(usage.Options):
	optParameters = [
		['config', 'c', 'settings.ini', 'Configuration file.'],
	]

class FSMonitor():
	def __init__(self, path, channel):
		self._messages = []
		self._callid = None
		self._bot = None
		self._channel = channel
		self._watch_path = filepath.FilePath(path)

		self._watchMask = (	  inotify.IN_MODIFY
			| inotify.IN_CREATE
			| inotify.IN_DELETE
			| inotify.IN_MOVED_FROM
			| inotify.IN_MOVED_TO
		)


		notifier = inotify.INotify()
		notifier.startReading()
		notifier.watch(self._watch_path, autoAdd=True, recursive=True, callbacks=[self.fsnotify], mask=self._watchMask)

	def setBot(self, bot):
		self._bot = bot

	def humanReadableMask(self, mask):
		flags_to_human = [
			(inotify.IN_MODIFY, 'geändert'),
			(inotify.IN_CREATE, 'erstellt'),
			(inotify.IN_DELETE, 'gelöscht'),
			(inotify.IN_MOVED_FROM, 'umbenannt von'),
			(inotify.IN_MOVED_TO, 'umbenannt nach')
		]

		"""In Maske enthaltene Flags als String zusammenbauen"""
		s = []
		for k, v in flags_to_human:
			if k & mask:
				s.append(v)
		return s

	def fsnotify(self, ignored, filepath, mask):
		"""Actually called by the notifier in case of any event."""
		if self._callid != None and self._callid.active():
			self._callid.cancel()
		path_segments = filepath.segmentsFrom(self._watch_path)
		new_path = '/'.join(path_segments)
		msg = "ftp> /%s (%s)" % (new_path, ', '.join(self.humanReadableMask(mask)))
		if msg not in self._messages:
			self._messages.append(msg)
		self._callid = reactor.callLater(10.0, self.sendQueuedMessages)

	def sendQueuedMessages(self):
		if self._bot == None:
			print("No Bot given, dropping messages!")
			return
		if len(self._messages) > 3:
			self._bot.msg(self._channel, "ftp> %i Events übersprungen. Letzter Event:" % (len(self._messages)-1))
			self._bot.msg(self._channel, self._messages[len(self._messages)-1])
		else:
			for msg in self._messages:
				self._bot.msg(self._channel, msg)
		self._messages = []


if __name__ == '__main__':
	options = Options()
	config = ConfigParser()
	config.read([options['config']])

	host = config.get('irc', 'host')
	port = int(config.get('irc', 'port'))
	channel = config.get('irc', 'channel')
	nickname = config.get('irc', 'nickname')
	realname = config.get('irc', 'realname')
	path = config.get('fsmonitor', 'path')

	fsmon = FSMonitor(path, channel)

	# create factory protocol and application
	f = MonitorBotFactory(nickname, channel, fsmon)

	# connect factory to this host and port
	reactor.connectTCP(host, port, f)

	# run bot
	reactor.run()
